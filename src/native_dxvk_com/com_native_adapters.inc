/* SPDX-License-Identifier: MIT; explicit x86/host layouts and mapping lifetime. */
struct ImageShape { uint32_t width=1,height=1,depth=1,mips=1,arrays=1;DXGI_FORMAT format=DXGI_FORMAT_UNKNOWN;uint32_t bytes=0; };
struct PixelLayout { uint32_t block_width=1,block_height=1,bytes=0; };
PixelLayout pixel_layout(DXGI_FORMAT format) {
    uint32_t f=uint32_t(format);
    if(f>=1&&f<=4)return {1,1,16};
    if(f>=5&&f<=8)return {1,1,12};
    if(f>=9&&f<=22)return {1,1,8};
    if(f>=23&&f<=47)return {1,1,4};
    if(f>=48&&f<=59)return {1,1,2};
    if(f>=60&&f<=65)return {1,1,1};
    if(f==66)return {8,1,1};
    if(f==67)return {1,1,4};
    if(f==68||f==69)return {2,1,4};
    if((f>=70&&f<=72)||(f>=79&&f<=81))return {4,4,8};
    if((f>=73&&f<=78)||(f>=82&&f<=84)||(f>=94&&f<=99))return {4,4,16};
    if(f==85||f==86||f==115)return {1,1,2};
    if((f>=87&&f<=93)||f==100||f==101)return {1,1,4};
    if(f==102)return {1,1,8};
    if(f==107)return {2,1,4};
    if(f==108||f==109)return {2,1,8};
    throw Fault(E_NOTIMPL); // Multi-planar video formats require a separate ABI adapter.
}
uint32_t checked_bytes(uint64_t value) {
    if(!value||value>512ull*1024*1024)throw Fault(E_INVALIDARG);
    return uint32_t(value);
}
uint32_t mip_count(uint32_t width,uint32_t height,uint32_t depth) {
    uint32_t n=std::max({width,height,depth}),mips=0;while(n){++mips;n>>=1;}return mips;
}
ImageShape resource_shape(ID3D11Resource* resource,uint32_t subresource) {
    if(!resource)throw Fault(E_POINTER);
    D3D11_RESOURCE_DIMENSION type;resource->GetType(&type);ImageShape s;
    if(type==D3D11_RESOURCE_DIMENSION_BUFFER) {
        D3D11_BUFFER_DESC desc;reinterpret_cast<ID3D11Buffer*>(resource)->GetDesc(&desc);s.bytes=desc.ByteWidth;
        if(subresource)throw Fault(E_INVALIDARG);
        return s;
    }
    if(type==D3D11_RESOURCE_DIMENSION_TEXTURE1D) {
        D3D11_TEXTURE1D_DESC d;reinterpret_cast<ID3D11Texture1D*>(resource)->GetDesc(&d);s.width=d.Width;s.mips=d.MipLevels;s.arrays=d.ArraySize;s.format=d.Format;
    } else if(type==D3D11_RESOURCE_DIMENSION_TEXTURE2D) {
        D3D11_TEXTURE2D_DESC d;reinterpret_cast<ID3D11Texture2D*>(resource)->GetDesc(&d);s.width=d.Width;s.height=d.Height;s.mips=d.MipLevels;s.arrays=d.ArraySize;s.format=d.Format;
    } else if(type==D3D11_RESOURCE_DIMENSION_TEXTURE3D) {
        D3D11_TEXTURE3D_DESC d;reinterpret_cast<ID3D11Texture3D*>(resource)->GetDesc(&d);s.width=d.Width;s.height=d.Height;s.depth=d.Depth;s.mips=d.MipLevels;s.format=d.Format;
    } else throw Fault(E_INVALIDARG);
    if(!s.mips||subresource>=uint64_t(s.mips)*s.arrays)throw Fault(E_INVALIDARG);
    uint32_t mip=subresource%s.mips;s.width=std::max(1u,s.width>>mip);s.height=std::max(1u,s.height>>mip);s.depth=std::max(1u,s.depth>>mip);return s;
}
uint32_t upload_bytes(const ImageShape& s,uint32_t row_pitch,uint32_t slice_pitch) {
    if(s.bytes)return checked_bytes(s.bytes);
    auto layout=pixel_layout(s.format);uint32_t rows=(s.height+layout.block_height-1)/layout.block_height;
    uint64_t row_bytes=uint64_t((s.width+layout.block_width-1)/layout.block_width)*layout.bytes;
    if((rows>1&&row_pitch<row_bytes)||(s.depth>1&&uint64_t(slice_pitch)<uint64_t(row_pitch)*rows))throw Fault(E_INVALIDARG);
    return checked_bytes(uint64_t(s.depth-1)*slice_pitch+uint64_t(rows-1)*row_pitch+row_bytes);
}
std::vector<D3D11_SUBRESOURCE_DATA> initial_data(Context& c,uint32_t address,ImageShape s) {
    if(!address)return {};
    const uint32_t maximum_mips=mip_count(s.width,s.height,s.depth);
    if(!s.width||!s.height||!s.depth||!s.arrays)throw Fault(E_INVALIDARG);
    if(!s.mips)s.mips=maximum_mips;
    if(s.mips>maximum_mips||uint64_t(s.mips)*s.arrays>SD_COM_MAX_ARRAY)throw Fault(E_INVALIDARG);
    uint32_t count=c.array_count(s.mips*s.arrays);
    auto wire=c.required_read<sd_com_subresource32>(address,count);std::vector<D3D11_SUBRESOURCE_DATA> result(count);
    for(uint32_t i=0;i<count;++i) {
        uint32_t mip=i%s.mips;ImageShape sub=s;sub.width=std::max(1u,s.width>>mip);sub.height=std::max(1u,s.height>>mip);sub.depth=std::max(1u,s.depth>>mip);
        uint32_t bytes=upload_bytes(sub,wire[i].row_pitch,wire[i].slice_pitch);
        result[i]={c.required_read<unsigned char>(wire[i].data,bytes),wire[i].row_pitch,wire[i].slice_pitch};
    }
    return result;
}
template<typename T> void custom_ID3D11Device_CreateBuffer(Context& c,T* device,sd_com_packet& p) {
    auto desc=c.required_read<D3D11_BUFFER_DESC>(p.args[0]);auto output=c.write<uint32_t>(p.args[2]);if(output)*output=0;
    ImageShape shape;shape.bytes=desc->ByteWidth;
    auto data=initial_data(c,p.args[1],shape);ID3D11Buffer* object=nullptr;
    p.ret=device->CreateBuffer(desc,data.empty()?nullptr:data.data(),output?&object:nullptr);
    if(SUCCEEDED(HRESULT(p.ret))&&output)*output=c.adopt(object,SD_COM_IF_ID3D11Buffer);
}
template<typename T> void custom_ID3D11Device_CreateTexture1D(Context& c,T* device,sd_com_packet& p) {
    auto desc=c.required_read<D3D11_TEXTURE1D_DESC>(p.args[0]);auto output=c.write<uint32_t>(p.args[2]);if(output)*output=0;
    ImageShape s;s.width=desc->Width;s.mips=desc->MipLevels;s.arrays=desc->ArraySize;s.format=desc->Format;
    auto data=initial_data(c,p.args[1],s);ID3D11Texture1D* object=nullptr;
    p.ret=device->CreateTexture1D(desc,data.empty()?nullptr:data.data(),output?&object:nullptr);
    if(SUCCEEDED(HRESULT(p.ret))&&output)*output=c.adopt(object,SD_COM_IF_ID3D11Texture1D);
}
template<typename T> void custom_ID3D11Device_CreateTexture2D(Context& c,T* device,sd_com_packet& p) {
    auto desc=c.required_read<D3D11_TEXTURE2D_DESC>(p.args[0]);auto output=c.write<uint32_t>(p.args[2]);if(output)*output=0;
    ImageShape s;s.width=desc->Width;s.height=desc->Height;s.mips=desc->MipLevels;s.arrays=desc->ArraySize;s.format=desc->Format;
    auto data=initial_data(c,p.args[1],s);ID3D11Texture2D* object=nullptr;
    p.ret=device->CreateTexture2D(desc,data.empty()?nullptr:data.data(),output?&object:nullptr);
    if(SUCCEEDED(HRESULT(p.ret))&&output)*output=c.adopt(object,SD_COM_IF_ID3D11Texture2D);
}
template<typename T> void custom_ID3D11Device_CreateTexture3D(Context& c,T* device,sd_com_packet& p) {
    auto desc=c.required_read<D3D11_TEXTURE3D_DESC>(p.args[0]);auto output=c.write<uint32_t>(p.args[2]);if(output)*output=0;
    ImageShape s;s.width=desc->Width;s.height=desc->Height;s.depth=desc->Depth;s.mips=desc->MipLevels;s.format=desc->Format;
    auto data=initial_data(c,p.args[1],s);ID3D11Texture3D* object=nullptr;
    p.ret=device->CreateTexture3D(desc,data.empty()?nullptr:data.data(),output?&object:nullptr);
    if(SUCCEEDED(HRESULT(p.ret))&&output)*output=c.adopt(object,SD_COM_IF_ID3D11Texture3D);
}
template<typename T> void custom_ID3D11Device_CreateInputLayout(Context& c,T* device,sd_com_packet& p) {
    uint32_t n=c.array_count(p.args[1]);auto source=c.read<sd_com_input32>(p.args[0],n);std::vector<D3D11_INPUT_ELEMENT_DESC> desc(source?n:0);
    for(uint32_t i=0;i<desc.size();++i)desc[i]={c.string(source[i].semantic),source[i].index,DXGI_FORMAT(source[i].format),source[i].slot,source[i].offset,D3D11_INPUT_CLASSIFICATION(source[i].slot_class),source[i].step};
    auto code=c.read<unsigned char>(p.args[2],p.args[3]);auto output=c.write<uint32_t>(p.args[4]);if(output)*output=0;ID3D11InputLayout* object=nullptr;
    p.ret=device->CreateInputLayout(source?desc.data():nullptr,n,code,p.args[3],output?&object:nullptr);
    if(SUCCEEDED(HRESULT(p.ret))&&output)*output=c.adopt(object,SD_COM_IF_ID3D11InputLayout);
}
template<typename T> void custom_ID3D11Device_CreateGeometryShaderWithStreamOutput(Context& c,T* device,sd_com_packet& p) {
    auto code=c.read<unsigned char>(p.args[0],p.args[1]);uint32_t n=c.array_count(p.args[3]);auto source=c.read<sd_com_so32>(p.args[2],n);std::vector<D3D11_SO_DECLARATION_ENTRY> desc(source?n:0);
    for(uint32_t i=0;i<desc.size();++i)desc[i]={source[i].stream,c.string(source[i].semantic),source[i].index,source[i].start,source[i].count,source[i].slot};
    auto strides=c.read<UINT>(p.args[4],c.array_count(p.args[5]));auto linkage=c.object<ID3D11ClassLinkage>(p.args[7],SD_COM_IF_ID3D11ClassLinkage);
    auto output=c.write<uint32_t>(p.args[8]);if(output)*output=0;ID3D11GeometryShader* object=nullptr;
    p.ret=device->CreateGeometryShaderWithStreamOutput(code,p.args[1],source?desc.data():nullptr,n,strides,p.args[5],p.args[6],linkage,output?&object:nullptr);
    if(SUCCEEDED(HRESULT(p.ret))&&output)*output=c.adopt(object,SD_COM_IF_ID3D11GeometryShader);
}
template<typename T> void custom_ID3D11DeviceContext_UpdateSubresource(Context& c,T* context,sd_com_packet& p) {
    auto resource=c.object<ID3D11Resource>(p.args[0],SD_COM_IF_ID3D11Resource);auto box=c.read<D3D11_BOX>(p.args[2]);
    // D3D11 treats empty boxes as no-ops before reading source data.
    if(box&&(box->right<=box->left||box->bottom<=box->top||box->back<=box->front)){p.ret=0;return;}
    auto shape=resource_shape(resource,p.args[1]);
    if(box) {
        if(shape.bytes)shape.bytes=box->right-box->left;
        else {shape.width=box->right-box->left;shape.height=box->bottom-box->top;shape.depth=box->back-box->front;}
    }
    uint32_t bytes=upload_bytes(shape,p.args[4],p.args[5]);auto data=c.required_read<unsigned char>(p.args[3],bytes);
    context->UpdateSubresource(resource,p.args[1],box,data,p.args[4],p.args[5]);p.ret=0;
}
template<typename T> void custom_ID3D11DeviceContext_Map(Context& c,T* context,sd_com_packet& p) {
    auto resource=c.object<ID3D11Resource>(p.args[0],SD_COM_IF_ID3D11Resource);auto output=c.required_write<sd_com_mapped32>(p.args[4]);*output={};
    auto shape=resource_shape(resource,p.args[1]);
    for(const auto& entry:c.maps)if(entry.second.context==context&&entry.second.resource==resource&&entry.second.subresource==p.args[1])throw Fault(E_INVALIDARG);
    D3D11_MAPPED_SUBRESOURCE native={};p.ret=context->Map(resource,p.args[1],D3D11_MAP(p.args[2]),p.args[3],&native);
    if(FAILED(HRESULT(p.ret)))return;
    uint32_t bytes=0;
    try {
        if(shape.bytes)bytes=checked_bytes(shape.bytes);
        else {auto layout=pixel_layout(shape.format);uint32_t rows=(shape.height+layout.block_height-1)/layout.block_height;
            bytes=checked_bytes(uint64_t(native.DepthPitch)*(shape.depth-1)+uint64_t(native.RowPitch)*rows);}
        if(!native.pData)throw Fault(E_FAIL);
        if(!c.next_map)throw Fault(E_OUTOFMEMORY);
        uint32_t id=c.next_map++;MapRecord record;record.id=id;record.context=context;record.resource=resource;record.subresource=p.args[1];record.type=p.args[2];record.bytes=bytes;record.native=native;
        c.maps.emplace(id,record);context->AddRef();resource->AddRef();
        output->row_pitch=native.RowPitch;output->depth_pitch=native.DepthPitch;p.high[0]=bytes;p.aux=id;
    }catch(...){context->Unmap(resource,p.args[1]);throw;}
}
template<typename T> void custom_ID3D11DeviceContext_Unmap(Context& c,T* context,sd_com_packet& p) {
    auto resource=c.object<ID3D11Resource>(p.args[0],SD_COM_IF_ID3D11Resource);uint32_t id=0;
    for(const auto& entry:c.maps)if(entry.second.context==context&&entry.second.resource==resource&&entry.second.subresource==p.args[1]){id=entry.first;break;}
    if(!id)throw Fault(E_INVALIDARG);
    auto& m=c.maps.at(id);
    if(!m.guest)throw Fault(E_INVALIDARG);
    if(m.type!=D3D11_MAP_READ){auto data=c.required_read<unsigned char>(m.guest,m.bytes);std::memcpy(m.native.pData,data,m.bytes);c.map_bytes+=m.bytes;}
    c.abort_map(id);p.aux=id;p.ret=0;
}
template<typename T> void private_set(Context& c,T* object,sd_com_packet& p) {
    const GUID value=*c.required_read<GUID>(p.args[0]);auto data=c.read<unsigned char>(p.args[2],p.args[1]);
    p.ret=object->SetPrivateData(value,p.args[1],data);
    if(SUCCEEDED(HRESULT(p.ret)))c.private_interfaces.erase({c.identity(object),value});
}
template<typename T> void private_interface(Context& c,T* object,sd_com_packet& p) {
    const GUID value=*c.required_read<GUID>(p.args[0]);auto data=c.object<IUnknown>(p.args[1],SD_COM_IF_IUnknown);
    p.ret=object->SetPrivateDataInterface(value,data);
    if(SUCCEEDED(HRESULT(p.ret))){auto key=PrivateKey{c.identity(object),value};if(data)c.private_interfaces[key]=true;else c.private_interfaces.erase(key);}
}
template<typename T> void private_get(Context& c,T* object,sd_com_packet& p) {
    const GUID value=*c.required_read<GUID>(p.args[0]);auto size=c.required_write<UINT>(p.args[1]);auto key=PrivateKey{c.identity(object),value};
    if(c.private_interfaces.count(key)) {
        if(!p.args[2]){*size=4;p.ret=S_OK;return;}
        if(*size<4){*size=4;p.ret=DXGI_ERROR_MORE_DATA;return;}
        auto output=c.required_write<uint32_t>(p.args[2]);IUnknown* data=nullptr;UINT bytes=sizeof(data);
        p.ret=object->GetPrivateData(value,&bytes,&data);*size=4;*output=0;
        if(SUCCEEDED(HRESULT(p.ret))){*output=c.adopt(data,SD_COM_IF_IUnknown);p.aux=SD_COM_PRIVATE_INTERFACE;}
        else if(HRESULT(p.ret)==DXGI_ERROR_NOT_FOUND)c.private_interfaces.erase(key);
    }else {auto output=c.write<unsigned char>(p.args[2],*size);p.ret=object->GetPrivateData(value,size,output);}
}
#define PRIVATE_ADAPTERS(Owner) \
template<typename T> void custom_##Owner##_SetPrivateData(Context& c,T* o,sd_com_packet& p){private_set(c,o,p);} \
template<typename T> void custom_##Owner##_SetPrivateDataInterface(Context& c,T* o,sd_com_packet& p){private_interface(c,o,p);} \
template<typename T> void custom_##Owner##_GetPrivateData(Context& c,T* o,sd_com_packet& p){private_get(c,o,p);}
PRIVATE_ADAPTERS(ID3D11Device)
PRIVATE_ADAPTERS(ID3D11DeviceChild)
PRIVATE_ADAPTERS(IDXGIObject)
#undef PRIVATE_ADAPTERS
thread_local std::vector<ID3D10Multithread*> entered_multithread;
template<typename T> void custom_ID3D10Multithread_Enter(Context& c,T* object,sd_com_packet& p){
    entered_multithread.push_back(object);c.mutex.lock();object->Enter();p.ret=0;
}
template<typename T> void custom_ID3D10Multithread_Leave(Context& c,T* object,sd_com_packet& p){
    if(entered_multithread.empty()||entered_multithread.back()!=object)throw Fault(E_INVALIDARG);
    object->Leave();entered_multithread.pop_back();p.ret=0;c.mutex.unlock();
}
template<typename T> void custom_ID3D11ClassInstance_GetInstanceName(Context& c,T* object,sd_com_packet& p) {
    auto size=c.required_write<uint32_t>(p.args[1]);SIZE_T length=*size;auto output=c.write<char>(p.args[0],length);
    object->GetInstanceName(output,&length);if(length>UINT32_MAX)throw Fault(E_FAIL);*size=uint32_t(length);p.ret=0;
}
template<typename T> void custom_ID3D11ClassInstance_GetTypeName(Context& c,T* object,sd_com_packet& p) {
    auto size=c.required_write<uint32_t>(p.args[1]);SIZE_T length=*size;auto output=c.write<char>(p.args[0],length);
    object->GetTypeName(output,&length);if(length>UINT32_MAX)throw Fault(E_FAIL);*size=uint32_t(length);p.ret=0;
}
template<typename T> void custom_ID3D11Device_CheckCounter(Context& c,T* object,sd_com_packet& p) {
    auto desc=c.read<D3D11_COUNTER_DESC>(p.args[0]);auto type=c.write<D3D11_COUNTER_TYPE>(p.args[1]);auto count=c.write<UINT>(p.args[2]);
    auto name_len=c.write<UINT>(p.args[4]);auto units_len=c.write<UINT>(p.args[6]);auto desc_len=c.write<UINT>(p.args[8]);
    auto name=c.write<char>(p.args[3],name_len?*name_len:0);auto units=c.write<char>(p.args[5],units_len?*units_len:0);auto description=c.write<char>(p.args[7],desc_len?*desc_len:0);
    p.ret=object->CheckCounter(desc,type,count,name,name_len,units,units_len,description,desc_len);
}
void wide32_to_16(const WCHAR* src,uint16_t* dst,size_t count) {
    std::fill_n(dst,count,0);size_t used=0;
    for(size_t i=0;i<count&&src[i]&&used+1<count;++i){uint32_t cp=uint32_t(src[i]);
        if(cp>0xffff&&cp<=0x10ffff&&used+2<count){cp-=0x10000;dst[used++]=uint16_t(0xd800+(cp>>10));dst[used++]=uint16_t(0xdc00+(cp&1023));}
        else dst[used++]=cp<=0xffff?uint16_t(cp):uint16_t(0xfffd);}
}
struct Adapter32 {uint16_t description[128];uint32_t vendor,device,subsys,revision,video,system,shared;LUID luid;};
struct Adapter1_32 {Adapter32 base;uint32_t flags;};
struct Output32 {uint16_t name[32];RECT rect;BOOL attached;DXGI_MODE_ROTATION rotation;uint32_t monitor;};
static_assert(sizeof(Adapter32)==292&&sizeof(Adapter1_32)==296&&sizeof(Output32)==92,"DXGI x86 layout");
template<typename T> void adapter_copy(const T& source,Adapter32& dest) {
    wide32_to_16(source.Description,dest.description,128);dest.vendor=source.VendorId;dest.device=source.DeviceId;dest.subsys=source.SubSysId;dest.revision=source.Revision;
    dest.video=uint32_t(std::min<SIZE_T>(source.DedicatedVideoMemory,UINT32_MAX));dest.system=uint32_t(std::min<SIZE_T>(source.DedicatedSystemMemory,UINT32_MAX));dest.shared=uint32_t(std::min<SIZE_T>(source.SharedSystemMemory,UINT32_MAX));dest.luid=source.AdapterLuid;
}
template<typename T> void custom_IDXGIAdapter_GetDesc(Context& c,T* object,sd_com_packet& p) {
    auto output=c.required_write<Adapter32>(p.args[0]);DXGI_ADAPTER_DESC desc={};p.ret=object->GetDesc(&desc);if(SUCCEEDED(HRESULT(p.ret)))adapter_copy(desc,*output);
}
template<typename T> void custom_IDXGIAdapter1_GetDesc1(Context& c,T* object,sd_com_packet& p) {
    auto output=c.required_write<Adapter1_32>(p.args[0]);DXGI_ADAPTER_DESC1 desc={};p.ret=object->GetDesc1(&desc);if(SUCCEEDED(HRESULT(p.ret))){adapter_copy(desc,output->base);output->flags=desc.Flags;}
}
template<typename T> void custom_IDXGIOutput_GetDesc(Context& c,T* object,sd_com_packet& p) {
    auto output=c.required_write<Output32>(p.args[0]);DXGI_OUTPUT_DESC desc={};p.ret=object->GetDesc(&desc);
    if(SUCCEEDED(HRESULT(p.ret))){wide32_to_16(desc.DeviceName,output->name,32);output->rect=desc.DesktopCoordinates;output->attached=desc.AttachedToDesktop;output->rotation=desc.Rotation;output->monitor=0;}
}
DXGI_SWAP_CHAIN_DESC swapchain_desc(const sd_com_swapchain32& source) {
    DXGI_SWAP_CHAIN_DESC desc={};static_assert(sizeof(desc.BufferDesc)==sizeof(source.mode),"mode ABI");
    std::memcpy(&desc.BufferDesc,source.mode,sizeof(source.mode));std::memcpy(&desc.SampleDesc,source.sample,sizeof(source.sample));
    desc.BufferDesc.Width=1280;desc.BufferDesc.Height=720;desc.BufferUsage=source.usage;desc.BufferCount=source.count;
    desc.OutputWindow=sd_com_native_window();if(!desc.OutputWindow)throw Fault(E_FAIL);
    desc.Windowed=TRUE;desc.SwapEffect=DXGI_SWAP_EFFECT(source.effect);desc.Flags=source.flags;return desc;
}
template<typename T> void custom_IDXGIFactory_CreateSwapChain(Context& c,T* object,sd_com_packet& p) {
    auto device=c.object<IUnknown>(p.args[0],SD_COM_IF_IUnknown);const auto wire=*c.required_read<sd_com_swapchain32>(p.args[1]);
    auto output=c.required_write<uint32_t>(p.args[2]);*output=0;auto desc=swapchain_desc(wire);IDXGISwapChain* swap=nullptr;
    p.ret=object->CreateSwapChain(device,&desc,&swap);
    if(SUCCEEDED(HRESULT(p.ret))){*output=c.adopt(swap,SD_COM_IF_IDXGISwapChain);auto& entry=c.slot(*output);entry.guest_window=wire.window;entry.fullscreen=!wire.windowed;
        wine_nx_runtime_trace("[SD-NDX-COM] SWAPCHAIN native 1280x720; trusted window; guest HWND retained as metadata");}
}
template<typename T> void custom_IDXGIFactory_MakeWindowAssociation(Context& c,T* object,sd_com_packet& p) {
    p.ret=object->MakeWindowAssociation(sd_com_native_window(),p.args[1]);
    if(SUCCEEDED(HRESULT(p.ret)))c.set_window_metadata(p.object,p.args[0],false);
}
template<typename T> void custom_IDXGIFactory_GetWindowAssociation(Context& c,T*,sd_com_packet& p) {
    *c.required_write<uint32_t>(p.args[0])=c.slot(p.object).guest_window;p.ret=S_OK;
}
template<typename T> void custom_IDXGISwapChain_GetDesc(Context& c,T* object,sd_com_packet& p) {
    auto output=c.required_write<sd_com_swapchain32>(p.args[0]);DXGI_SWAP_CHAIN_DESC desc={};p.ret=object->GetDesc(&desc);
    if(SUCCEEDED(HRESULT(p.ret))){std::memcpy(output->mode,&desc.BufferDesc,sizeof(output->mode));std::memcpy(output->sample,&desc.SampleDesc,sizeof(output->sample));
        auto& entry=c.slot(p.object);output->usage=desc.BufferUsage;output->count=desc.BufferCount;output->window=entry.guest_window;output->windowed=!entry.fullscreen;output->effect=desc.SwapEffect;output->flags=desc.Flags;}
}
template<typename T> void custom_IDXGISwapChain_SetFullscreenState(Context& c,T* object,sd_com_packet& p) {
    // Horizon owns display mode. Preserve the game's state while retaining a
    // windowed native surface and its fixed 720p allocation.
    if(p.args[1])c.object<IDXGIOutput>(p.args[1],SD_COM_IF_IDXGIOutput);
    p.ret=object->SetFullscreenState(FALSE,nullptr);if(SUCCEEDED(HRESULT(p.ret)))c.set_window_metadata(p.object,c.slot(p.object).guest_window,!!p.args[0]);
}
template<typename T> void custom_IDXGISwapChain_GetFullscreenState(Context& c,T* object,sd_com_packet& p) {
    auto output=c.write<BOOL>(p.args[0]);auto target=c.write<uint32_t>(p.args[1]);auto& entry=c.slot(p.object);
    if(output)*output=entry.fullscreen;
    if(target)*target=0;
    p.ret=S_OK;
    if(target&&entry.fullscreen){IDXGIOutput* native=nullptr;p.ret=object->GetContainingOutput(&native);if(SUCCEEDED(HRESULT(p.ret)))*target=c.adopt(native,SD_COM_IF_IDXGIOutput);}
}
template<typename T> void custom_IDXGISwapChain_ResizeBuffers(Context&,T* object,sd_com_packet& p) {
    p.ret=object->ResizeBuffers(p.args[0],1280,720,DXGI_FORMAT(p.args[3]),p.args[4]);
}
template<typename T> void custom_IDXGISwapChain_Present(Context& c,T* object,sd_com_packet& p) {
    p.ret=object->Present(p.args[0],p.args[1]);
    if(!(p.args[1]&DXGI_PRESENT_TEST)&&p.ret==S_OK) {
        ++c.presents;sd_com_presented(p.object,HRESULT(p.ret));
    }
}
template<typename T> void custom_IDXGISurface_Map(Context& c,T*,sd_com_packet& p){c.unsupported(p,"IDXGISurface::Map");}
template<typename T> void custom_IDXGISurface_Unmap(Context& c,T*,sd_com_packet& p){c.unsupported(p,"IDXGISurface::Unmap");}
