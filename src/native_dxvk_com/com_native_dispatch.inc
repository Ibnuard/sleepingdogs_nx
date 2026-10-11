case SD_COM_IF_ID3D10Multithread: {
    auto object = c.object<ID3D10Multithread>(p.object, SD_COM_IF_ID3D10Multithread);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D10Multithread::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D10Multithread::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D10Multithread::Release
    return c.Release(p);
}
case 3: { // ID3D10Multithread::Enter
    return custom_ID3D10Multithread_Enter(c, object, p);
}
case 4: { // ID3D10Multithread::Leave
    return custom_ID3D10Multithread_Leave(c, object, p);
}
case 5: { // ID3D10Multithread::SetMultithreadProtected
    auto bMTProtect = (WINBOOL)p.args[0];
    auto result = object->SetMultithreadProtected(bMTProtect);
    p.ret = result;
    return;
}
case 6: { // ID3D10Multithread::GetMultithreadProtected
    auto result = object->GetMultithreadProtected();
    p.ret = result;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11Asynchronous: {
    auto object = c.object<ID3D11Asynchronous>(p.object, SD_COM_IF_ID3D11Asynchronous);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11Asynchronous::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11Asynchronous::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11Asynchronous::Release
    return c.Release(p);
}
case 3: { // ID3D11Asynchronous::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11Asynchronous::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11Asynchronous::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11Asynchronous::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
case 7: { // ID3D11Asynchronous::GetDataSize
    auto result = object->GetDataSize();
    p.ret = result;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11BlendState: {
    auto object = c.object<ID3D11BlendState>(p.object, SD_COM_IF_ID3D11BlendState);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11BlendState::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11BlendState::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11BlendState::Release
    return c.Release(p);
}
case 3: { // ID3D11BlendState::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11BlendState::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11BlendState::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11BlendState::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
case 7: { // ID3D11BlendState::GetDesc
    auto pDesc = c.write<D3D11_BLEND_DESC>(p.args[0], c.array_count(1));
    object->GetDesc(pDesc);
    p.ret = 0;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11Buffer: {
    auto object = c.object<ID3D11Buffer>(p.object, SD_COM_IF_ID3D11Buffer);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11Buffer::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11Buffer::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11Buffer::Release
    return c.Release(p);
}
case 3: { // ID3D11Buffer::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11Buffer::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11Buffer::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11Buffer::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
case 7: { // ID3D11Buffer::GetType
    auto pResourceDimension = c.write<D3D11_RESOURCE_DIMENSION>(p.args[0], c.array_count(1));
    object->GetType(pResourceDimension);
    p.ret = 0;
    return;
}
case 8: { // ID3D11Buffer::SetEvictionPriority
    auto EvictionPriority = (UINT)p.args[0];
    object->SetEvictionPriority(EvictionPriority);
    p.ret = 0;
    return;
}
case 9: { // ID3D11Buffer::GetEvictionPriority
    auto result = object->GetEvictionPriority();
    p.ret = result;
    return;
}
case 10: { // ID3D11Buffer::GetDesc
    auto pDesc = c.write<D3D11_BUFFER_DESC>(p.args[0], c.array_count(1));
    object->GetDesc(pDesc);
    p.ret = 0;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11ClassInstance: {
    auto object = c.object<ID3D11ClassInstance>(p.object, SD_COM_IF_ID3D11ClassInstance);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11ClassInstance::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11ClassInstance::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11ClassInstance::Release
    return c.Release(p);
}
case 3: { // ID3D11ClassInstance::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11ClassInstance::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11ClassInstance::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11ClassInstance::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
case 7: { // ID3D11ClassInstance::GetClassLinkage
    const uint32_t count_ppLinkage = c.array_count(1);
    auto guest_ppLinkage = c.write<uint32_t>(p.args[0], count_ppLinkage);
    if (guest_ppLinkage) std::fill_n(guest_ppLinkage, count_ppLinkage, 0u);
    std::vector<ID3D11ClassLinkage*> native_ppLinkage(count_ppLinkage, nullptr);
    auto ppLinkage = guest_ppLinkage ? native_ppLinkage.data() : nullptr;
    object->GetClassLinkage(ppLinkage);
    if (guest_ppLinkage) for (uint32_t i=0; i<count_ppLinkage; ++i) guest_ppLinkage[i] = c.adopt(native_ppLinkage[i], SD_COM_IF_ID3D11ClassLinkage);
    p.ret = 0;
    return;
}
case 8: { // ID3D11ClassInstance::GetDesc
    auto pDesc = c.write<D3D11_CLASS_INSTANCE_DESC>(p.args[0], c.array_count(1));
    object->GetDesc(pDesc);
    p.ret = 0;
    return;
}
case 9: { // ID3D11ClassInstance::GetInstanceName
    return custom_ID3D11ClassInstance_GetInstanceName(c, object, p);
}
case 10: { // ID3D11ClassInstance::GetTypeName
    return custom_ID3D11ClassInstance_GetTypeName(c, object, p);
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11ClassLinkage: {
    auto object = c.object<ID3D11ClassLinkage>(p.object, SD_COM_IF_ID3D11ClassLinkage);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11ClassLinkage::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11ClassLinkage::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11ClassLinkage::Release
    return c.Release(p);
}
case 3: { // ID3D11ClassLinkage::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11ClassLinkage::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11ClassLinkage::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11ClassLinkage::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
case 7: { // ID3D11ClassLinkage::GetClassInstance
    auto InstanceIndex = (UINT)p.args[1];
    auto pClassInstanceName = c.string(p.args[0]);
    const uint32_t count_ppInstance = c.array_count(1);
    auto guest_ppInstance = c.write<uint32_t>(p.args[2], count_ppInstance);
    if (guest_ppInstance) std::fill_n(guest_ppInstance, count_ppInstance, 0u);
    std::vector<ID3D11ClassInstance*> native_ppInstance(count_ppInstance, nullptr);
    auto ppInstance = guest_ppInstance ? native_ppInstance.data() : nullptr;
    auto result = object->GetClassInstance(pClassInstanceName, InstanceIndex, ppInstance);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_ppInstance) for (uint32_t i=0; i<count_ppInstance; ++i) guest_ppInstance[i] = c.adopt(native_ppInstance[i], SD_COM_IF_ID3D11ClassInstance);
    p.ret = result;
    return;
}
case 8: { // ID3D11ClassLinkage::CreateClassInstance
    auto ConstantBufferOffset = (UINT)p.args[1];
    auto ConstantVectorOffset = (UINT)p.args[2];
    auto TextureOffset = (UINT)p.args[3];
    auto SamplerOffset = (UINT)p.args[4];
    auto pClassTypeName = c.string(p.args[0]);
    const uint32_t count_ppInstance = c.array_count(1);
    auto guest_ppInstance = c.write<uint32_t>(p.args[5], count_ppInstance);
    if (guest_ppInstance) std::fill_n(guest_ppInstance, count_ppInstance, 0u);
    std::vector<ID3D11ClassInstance*> native_ppInstance(count_ppInstance, nullptr);
    auto ppInstance = guest_ppInstance ? native_ppInstance.data() : nullptr;
    auto result = object->CreateClassInstance(pClassTypeName, ConstantBufferOffset, ConstantVectorOffset, TextureOffset, SamplerOffset, ppInstance);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_ppInstance) for (uint32_t i=0; i<count_ppInstance; ++i) guest_ppInstance[i] = c.adopt(native_ppInstance[i], SD_COM_IF_ID3D11ClassInstance);
    p.ret = result;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11CommandList: {
    auto object = c.object<ID3D11CommandList>(p.object, SD_COM_IF_ID3D11CommandList);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11CommandList::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11CommandList::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11CommandList::Release
    return c.Release(p);
}
case 3: { // ID3D11CommandList::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11CommandList::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11CommandList::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11CommandList::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
case 7: { // ID3D11CommandList::GetContextFlags
    auto result = object->GetContextFlags();
    p.ret = result;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11ComputeShader: {
    auto object = c.object<ID3D11ComputeShader>(p.object, SD_COM_IF_ID3D11ComputeShader);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11ComputeShader::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11ComputeShader::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11ComputeShader::Release
    return c.Release(p);
}
case 3: { // ID3D11ComputeShader::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11ComputeShader::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11ComputeShader::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11ComputeShader::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11Counter: {
    auto object = c.object<ID3D11Counter>(p.object, SD_COM_IF_ID3D11Counter);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11Counter::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11Counter::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11Counter::Release
    return c.Release(p);
}
case 3: { // ID3D11Counter::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11Counter::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11Counter::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11Counter::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
case 7: { // ID3D11Counter::GetDataSize
    auto result = object->GetDataSize();
    p.ret = result;
    return;
}
case 8: { // ID3D11Counter::GetDesc
    auto pDesc = c.write<D3D11_COUNTER_DESC>(p.args[0], c.array_count(1));
    object->GetDesc(pDesc);
    p.ret = 0;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11DepthStencilState: {
    auto object = c.object<ID3D11DepthStencilState>(p.object, SD_COM_IF_ID3D11DepthStencilState);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11DepthStencilState::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11DepthStencilState::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11DepthStencilState::Release
    return c.Release(p);
}
case 3: { // ID3D11DepthStencilState::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11DepthStencilState::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11DepthStencilState::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11DepthStencilState::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
case 7: { // ID3D11DepthStencilState::GetDesc
    auto pDesc = c.write<D3D11_DEPTH_STENCIL_DESC>(p.args[0], c.array_count(1));
    object->GetDesc(pDesc);
    p.ret = 0;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11DepthStencilView: {
    auto object = c.object<ID3D11DepthStencilView>(p.object, SD_COM_IF_ID3D11DepthStencilView);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11DepthStencilView::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11DepthStencilView::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11DepthStencilView::Release
    return c.Release(p);
}
case 3: { // ID3D11DepthStencilView::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11DepthStencilView::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11DepthStencilView::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11DepthStencilView::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
case 7: { // ID3D11DepthStencilView::GetResource
    const uint32_t count_ppResource = c.array_count(1);
    auto guest_ppResource = c.write<uint32_t>(p.args[0], count_ppResource);
    if (guest_ppResource) std::fill_n(guest_ppResource, count_ppResource, 0u);
    std::vector<ID3D11Resource*> native_ppResource(count_ppResource, nullptr);
    auto ppResource = guest_ppResource ? native_ppResource.data() : nullptr;
    object->GetResource(ppResource);
    if (guest_ppResource) for (uint32_t i=0; i<count_ppResource; ++i) guest_ppResource[i] = c.adopt(native_ppResource[i], SD_COM_IF_ID3D11Resource);
    p.ret = 0;
    return;
}
case 8: { // ID3D11DepthStencilView::GetDesc
    auto pDesc = c.write<D3D11_DEPTH_STENCIL_VIEW_DESC>(p.args[0], c.array_count(1));
    object->GetDesc(pDesc);
    p.ret = 0;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11Device: {
    auto object = c.object<ID3D11Device>(p.object, SD_COM_IF_ID3D11Device);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11Device::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11Device::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11Device::Release
    return c.Release(p);
}
case 3: { // ID3D11Device::CreateBuffer
    return custom_ID3D11Device_CreateBuffer(c, object, p);
}
case 4: { // ID3D11Device::CreateTexture1D
    return custom_ID3D11Device_CreateTexture1D(c, object, p);
}
case 5: { // ID3D11Device::CreateTexture2D
    return custom_ID3D11Device_CreateTexture2D(c, object, p);
}
case 6: { // ID3D11Device::CreateTexture3D
    return custom_ID3D11Device_CreateTexture3D(c, object, p);
}
case 7: { // ID3D11Device::CreateShaderResourceView
    auto pResource = c.object<ID3D11Resource>(p.args[0], SD_COM_IF_ID3D11Resource);
    auto pDesc = c.read<D3D11_SHADER_RESOURCE_VIEW_DESC>(p.args[1], c.array_count(1));
    const uint32_t count_ppSRView = c.array_count(1);
    auto guest_ppSRView = c.write<uint32_t>(p.args[2], count_ppSRView);
    if (guest_ppSRView) std::fill_n(guest_ppSRView, count_ppSRView, 0u);
    std::vector<ID3D11ShaderResourceView*> native_ppSRView(count_ppSRView, nullptr);
    auto ppSRView = guest_ppSRView ? native_ppSRView.data() : nullptr;
    auto result = object->CreateShaderResourceView(pResource, pDesc, ppSRView);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_ppSRView) for (uint32_t i=0; i<count_ppSRView; ++i) guest_ppSRView[i] = c.adopt(native_ppSRView[i], SD_COM_IF_ID3D11ShaderResourceView);
    p.ret = result;
    return;
}
case 8: { // ID3D11Device::CreateUnorderedAccessView
    auto pResource = c.object<ID3D11Resource>(p.args[0], SD_COM_IF_ID3D11Resource);
    auto pDesc = c.read<D3D11_UNORDERED_ACCESS_VIEW_DESC>(p.args[1], c.array_count(1));
    const uint32_t count_ppUAView = c.array_count(1);
    auto guest_ppUAView = c.write<uint32_t>(p.args[2], count_ppUAView);
    if (guest_ppUAView) std::fill_n(guest_ppUAView, count_ppUAView, 0u);
    std::vector<ID3D11UnorderedAccessView*> native_ppUAView(count_ppUAView, nullptr);
    auto ppUAView = guest_ppUAView ? native_ppUAView.data() : nullptr;
    auto result = object->CreateUnorderedAccessView(pResource, pDesc, ppUAView);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_ppUAView) for (uint32_t i=0; i<count_ppUAView; ++i) guest_ppUAView[i] = c.adopt(native_ppUAView[i], SD_COM_IF_ID3D11UnorderedAccessView);
    p.ret = result;
    return;
}
case 9: { // ID3D11Device::CreateRenderTargetView
    auto pResource = c.object<ID3D11Resource>(p.args[0], SD_COM_IF_ID3D11Resource);
    auto pDesc = c.read<D3D11_RENDER_TARGET_VIEW_DESC>(p.args[1], c.array_count(1));
    const uint32_t count_ppRTView = c.array_count(1);
    auto guest_ppRTView = c.write<uint32_t>(p.args[2], count_ppRTView);
    if (guest_ppRTView) std::fill_n(guest_ppRTView, count_ppRTView, 0u);
    std::vector<ID3D11RenderTargetView*> native_ppRTView(count_ppRTView, nullptr);
    auto ppRTView = guest_ppRTView ? native_ppRTView.data() : nullptr;
    auto result = object->CreateRenderTargetView(pResource, pDesc, ppRTView);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_ppRTView) for (uint32_t i=0; i<count_ppRTView; ++i) guest_ppRTView[i] = c.adopt(native_ppRTView[i], SD_COM_IF_ID3D11RenderTargetView);
    p.ret = result;
    return;
}
case 10: { // ID3D11Device::CreateDepthStencilView
    auto pResource = c.object<ID3D11Resource>(p.args[0], SD_COM_IF_ID3D11Resource);
    auto pDesc = c.read<D3D11_DEPTH_STENCIL_VIEW_DESC>(p.args[1], c.array_count(1));
    const uint32_t count_ppDepthStencilView = c.array_count(1);
    auto guest_ppDepthStencilView = c.write<uint32_t>(p.args[2], count_ppDepthStencilView);
    if (guest_ppDepthStencilView) std::fill_n(guest_ppDepthStencilView, count_ppDepthStencilView, 0u);
    std::vector<ID3D11DepthStencilView*> native_ppDepthStencilView(count_ppDepthStencilView, nullptr);
    auto ppDepthStencilView = guest_ppDepthStencilView ? native_ppDepthStencilView.data() : nullptr;
    auto result = object->CreateDepthStencilView(pResource, pDesc, ppDepthStencilView);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_ppDepthStencilView) for (uint32_t i=0; i<count_ppDepthStencilView; ++i) guest_ppDepthStencilView[i] = c.adopt(native_ppDepthStencilView[i], SD_COM_IF_ID3D11DepthStencilView);
    p.ret = result;
    return;
}
case 11: { // ID3D11Device::CreateInputLayout
    return custom_ID3D11Device_CreateInputLayout(c, object, p);
}
case 12: { // ID3D11Device::CreateVertexShader
    auto BytecodeLength = (SIZE_T)p.args[1];
    auto pShaderBytecode = c.read<unsigned char>(p.args[0], BytecodeLength);
    auto pClassLinkage = c.object<ID3D11ClassLinkage>(p.args[2], SD_COM_IF_ID3D11ClassLinkage);
    const uint32_t count_ppVertexShader = c.array_count(1);
    auto guest_ppVertexShader = c.write<uint32_t>(p.args[3], count_ppVertexShader);
    if (guest_ppVertexShader) std::fill_n(guest_ppVertexShader, count_ppVertexShader, 0u);
    std::vector<ID3D11VertexShader*> native_ppVertexShader(count_ppVertexShader, nullptr);
    auto ppVertexShader = guest_ppVertexShader ? native_ppVertexShader.data() : nullptr;
    auto result = object->CreateVertexShader(pShaderBytecode, BytecodeLength, pClassLinkage, ppVertexShader);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_ppVertexShader) for (uint32_t i=0; i<count_ppVertexShader; ++i) guest_ppVertexShader[i] = c.adopt(native_ppVertexShader[i], SD_COM_IF_ID3D11VertexShader);
    p.ret = result;
    return;
}
case 13: { // ID3D11Device::CreateGeometryShader
    auto BytecodeLength = (SIZE_T)p.args[1];
    auto pShaderBytecode = c.read<unsigned char>(p.args[0], BytecodeLength);
    auto pClassLinkage = c.object<ID3D11ClassLinkage>(p.args[2], SD_COM_IF_ID3D11ClassLinkage);
    const uint32_t count_ppGeometryShader = c.array_count(1);
    auto guest_ppGeometryShader = c.write<uint32_t>(p.args[3], count_ppGeometryShader);
    if (guest_ppGeometryShader) std::fill_n(guest_ppGeometryShader, count_ppGeometryShader, 0u);
    std::vector<ID3D11GeometryShader*> native_ppGeometryShader(count_ppGeometryShader, nullptr);
    auto ppGeometryShader = guest_ppGeometryShader ? native_ppGeometryShader.data() : nullptr;
    auto result = object->CreateGeometryShader(pShaderBytecode, BytecodeLength, pClassLinkage, ppGeometryShader);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_ppGeometryShader) for (uint32_t i=0; i<count_ppGeometryShader; ++i) guest_ppGeometryShader[i] = c.adopt(native_ppGeometryShader[i], SD_COM_IF_ID3D11GeometryShader);
    p.ret = result;
    return;
}
case 14: { // ID3D11Device::CreateGeometryShaderWithStreamOutput
    return custom_ID3D11Device_CreateGeometryShaderWithStreamOutput(c, object, p);
}
case 15: { // ID3D11Device::CreatePixelShader
    auto BytecodeLength = (SIZE_T)p.args[1];
    auto pShaderBytecode = c.read<unsigned char>(p.args[0], BytecodeLength);
    auto pClassLinkage = c.object<ID3D11ClassLinkage>(p.args[2], SD_COM_IF_ID3D11ClassLinkage);
    const uint32_t count_ppPixelShader = c.array_count(1);
    auto guest_ppPixelShader = c.write<uint32_t>(p.args[3], count_ppPixelShader);
    if (guest_ppPixelShader) std::fill_n(guest_ppPixelShader, count_ppPixelShader, 0u);
    std::vector<ID3D11PixelShader*> native_ppPixelShader(count_ppPixelShader, nullptr);
    auto ppPixelShader = guest_ppPixelShader ? native_ppPixelShader.data() : nullptr;
    auto result = object->CreatePixelShader(pShaderBytecode, BytecodeLength, pClassLinkage, ppPixelShader);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_ppPixelShader) for (uint32_t i=0; i<count_ppPixelShader; ++i) guest_ppPixelShader[i] = c.adopt(native_ppPixelShader[i], SD_COM_IF_ID3D11PixelShader);
    p.ret = result;
    return;
}
case 16: { // ID3D11Device::CreateHullShader
    auto BytecodeLength = (SIZE_T)p.args[1];
    auto pShaderBytecode = c.read<unsigned char>(p.args[0], BytecodeLength);
    auto pClassLinkage = c.object<ID3D11ClassLinkage>(p.args[2], SD_COM_IF_ID3D11ClassLinkage);
    const uint32_t count_ppHullShader = c.array_count(1);
    auto guest_ppHullShader = c.write<uint32_t>(p.args[3], count_ppHullShader);
    if (guest_ppHullShader) std::fill_n(guest_ppHullShader, count_ppHullShader, 0u);
    std::vector<ID3D11HullShader*> native_ppHullShader(count_ppHullShader, nullptr);
    auto ppHullShader = guest_ppHullShader ? native_ppHullShader.data() : nullptr;
    auto result = object->CreateHullShader(pShaderBytecode, BytecodeLength, pClassLinkage, ppHullShader);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_ppHullShader) for (uint32_t i=0; i<count_ppHullShader; ++i) guest_ppHullShader[i] = c.adopt(native_ppHullShader[i], SD_COM_IF_ID3D11HullShader);
    p.ret = result;
    return;
}
case 17: { // ID3D11Device::CreateDomainShader
    auto BytecodeLength = (SIZE_T)p.args[1];
    auto pShaderBytecode = c.read<unsigned char>(p.args[0], BytecodeLength);
    auto pClassLinkage = c.object<ID3D11ClassLinkage>(p.args[2], SD_COM_IF_ID3D11ClassLinkage);
    const uint32_t count_ppDomainShader = c.array_count(1);
    auto guest_ppDomainShader = c.write<uint32_t>(p.args[3], count_ppDomainShader);
    if (guest_ppDomainShader) std::fill_n(guest_ppDomainShader, count_ppDomainShader, 0u);
    std::vector<ID3D11DomainShader*> native_ppDomainShader(count_ppDomainShader, nullptr);
    auto ppDomainShader = guest_ppDomainShader ? native_ppDomainShader.data() : nullptr;
    auto result = object->CreateDomainShader(pShaderBytecode, BytecodeLength, pClassLinkage, ppDomainShader);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_ppDomainShader) for (uint32_t i=0; i<count_ppDomainShader; ++i) guest_ppDomainShader[i] = c.adopt(native_ppDomainShader[i], SD_COM_IF_ID3D11DomainShader);
    p.ret = result;
    return;
}
case 18: { // ID3D11Device::CreateComputeShader
    auto BytecodeLength = (SIZE_T)p.args[1];
    auto pShaderBytecode = c.read<unsigned char>(p.args[0], BytecodeLength);
    auto pClassLinkage = c.object<ID3D11ClassLinkage>(p.args[2], SD_COM_IF_ID3D11ClassLinkage);
    const uint32_t count_ppComputeShader = c.array_count(1);
    auto guest_ppComputeShader = c.write<uint32_t>(p.args[3], count_ppComputeShader);
    if (guest_ppComputeShader) std::fill_n(guest_ppComputeShader, count_ppComputeShader, 0u);
    std::vector<ID3D11ComputeShader*> native_ppComputeShader(count_ppComputeShader, nullptr);
    auto ppComputeShader = guest_ppComputeShader ? native_ppComputeShader.data() : nullptr;
    auto result = object->CreateComputeShader(pShaderBytecode, BytecodeLength, pClassLinkage, ppComputeShader);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_ppComputeShader) for (uint32_t i=0; i<count_ppComputeShader; ++i) guest_ppComputeShader[i] = c.adopt(native_ppComputeShader[i], SD_COM_IF_ID3D11ComputeShader);
    p.ret = result;
    return;
}
case 19: { // ID3D11Device::CreateClassLinkage
    const uint32_t count_ppLinkage = c.array_count(1);
    auto guest_ppLinkage = c.write<uint32_t>(p.args[0], count_ppLinkage);
    if (guest_ppLinkage) std::fill_n(guest_ppLinkage, count_ppLinkage, 0u);
    std::vector<ID3D11ClassLinkage*> native_ppLinkage(count_ppLinkage, nullptr);
    auto ppLinkage = guest_ppLinkage ? native_ppLinkage.data() : nullptr;
    auto result = object->CreateClassLinkage(ppLinkage);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_ppLinkage) for (uint32_t i=0; i<count_ppLinkage; ++i) guest_ppLinkage[i] = c.adopt(native_ppLinkage[i], SD_COM_IF_ID3D11ClassLinkage);
    p.ret = result;
    return;
}
case 20: { // ID3D11Device::CreateBlendState
    auto pBlendStateDesc = c.read<D3D11_BLEND_DESC>(p.args[0], c.array_count(1));
    const uint32_t count_ppBlendState = c.array_count(1);
    auto guest_ppBlendState = c.write<uint32_t>(p.args[1], count_ppBlendState);
    if (guest_ppBlendState) std::fill_n(guest_ppBlendState, count_ppBlendState, 0u);
    std::vector<ID3D11BlendState*> native_ppBlendState(count_ppBlendState, nullptr);
    auto ppBlendState = guest_ppBlendState ? native_ppBlendState.data() : nullptr;
    auto result = object->CreateBlendState(pBlendStateDesc, ppBlendState);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_ppBlendState) for (uint32_t i=0; i<count_ppBlendState; ++i) guest_ppBlendState[i] = c.adopt(native_ppBlendState[i], SD_COM_IF_ID3D11BlendState);
    p.ret = result;
    return;
}
case 21: { // ID3D11Device::CreateDepthStencilState
    auto pDepthStencilDesc = c.read<D3D11_DEPTH_STENCIL_DESC>(p.args[0], c.array_count(1));
    const uint32_t count_ppDepthStencilState = c.array_count(1);
    auto guest_ppDepthStencilState = c.write<uint32_t>(p.args[1], count_ppDepthStencilState);
    if (guest_ppDepthStencilState) std::fill_n(guest_ppDepthStencilState, count_ppDepthStencilState, 0u);
    std::vector<ID3D11DepthStencilState*> native_ppDepthStencilState(count_ppDepthStencilState, nullptr);
    auto ppDepthStencilState = guest_ppDepthStencilState ? native_ppDepthStencilState.data() : nullptr;
    auto result = object->CreateDepthStencilState(pDepthStencilDesc, ppDepthStencilState);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_ppDepthStencilState) for (uint32_t i=0; i<count_ppDepthStencilState; ++i) guest_ppDepthStencilState[i] = c.adopt(native_ppDepthStencilState[i], SD_COM_IF_ID3D11DepthStencilState);
    p.ret = result;
    return;
}
case 22: { // ID3D11Device::CreateRasterizerState
    auto pRasterizerDesc = c.read<D3D11_RASTERIZER_DESC>(p.args[0], c.array_count(1));
    const uint32_t count_ppRasterizerState = c.array_count(1);
    auto guest_ppRasterizerState = c.write<uint32_t>(p.args[1], count_ppRasterizerState);
    if (guest_ppRasterizerState) std::fill_n(guest_ppRasterizerState, count_ppRasterizerState, 0u);
    std::vector<ID3D11RasterizerState*> native_ppRasterizerState(count_ppRasterizerState, nullptr);
    auto ppRasterizerState = guest_ppRasterizerState ? native_ppRasterizerState.data() : nullptr;
    auto result = object->CreateRasterizerState(pRasterizerDesc, ppRasterizerState);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_ppRasterizerState) for (uint32_t i=0; i<count_ppRasterizerState; ++i) guest_ppRasterizerState[i] = c.adopt(native_ppRasterizerState[i], SD_COM_IF_ID3D11RasterizerState);
    p.ret = result;
    return;
}
case 23: { // ID3D11Device::CreateSamplerState
    auto pSamplerDesc = c.read<D3D11_SAMPLER_DESC>(p.args[0], c.array_count(1));
    const uint32_t count_ppSamplerState = c.array_count(1);
    auto guest_ppSamplerState = c.write<uint32_t>(p.args[1], count_ppSamplerState);
    if (guest_ppSamplerState) std::fill_n(guest_ppSamplerState, count_ppSamplerState, 0u);
    std::vector<ID3D11SamplerState*> native_ppSamplerState(count_ppSamplerState, nullptr);
    auto ppSamplerState = guest_ppSamplerState ? native_ppSamplerState.data() : nullptr;
    auto result = object->CreateSamplerState(pSamplerDesc, ppSamplerState);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_ppSamplerState) for (uint32_t i=0; i<count_ppSamplerState; ++i) guest_ppSamplerState[i] = c.adopt(native_ppSamplerState[i], SD_COM_IF_ID3D11SamplerState);
    p.ret = result;
    return;
}
case 24: { // ID3D11Device::CreateQuery
    auto pQueryDesc = c.read<D3D11_QUERY_DESC>(p.args[0], c.array_count(1));
    const uint32_t count_ppQuery = c.array_count(1);
    auto guest_ppQuery = c.write<uint32_t>(p.args[1], count_ppQuery);
    if (guest_ppQuery) std::fill_n(guest_ppQuery, count_ppQuery, 0u);
    std::vector<ID3D11Query*> native_ppQuery(count_ppQuery, nullptr);
    auto ppQuery = guest_ppQuery ? native_ppQuery.data() : nullptr;
    auto result = object->CreateQuery(pQueryDesc, ppQuery);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_ppQuery) for (uint32_t i=0; i<count_ppQuery; ++i) guest_ppQuery[i] = c.adopt(native_ppQuery[i], SD_COM_IF_ID3D11Query);
    p.ret = result;
    return;
}
case 25: { // ID3D11Device::CreatePredicate
    auto pPredicateDesc = c.read<D3D11_QUERY_DESC>(p.args[0], c.array_count(1));
    const uint32_t count_ppPredicate = c.array_count(1);
    auto guest_ppPredicate = c.write<uint32_t>(p.args[1], count_ppPredicate);
    if (guest_ppPredicate) std::fill_n(guest_ppPredicate, count_ppPredicate, 0u);
    std::vector<ID3D11Predicate*> native_ppPredicate(count_ppPredicate, nullptr);
    auto ppPredicate = guest_ppPredicate ? native_ppPredicate.data() : nullptr;
    auto result = object->CreatePredicate(pPredicateDesc, ppPredicate);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_ppPredicate) for (uint32_t i=0; i<count_ppPredicate; ++i) guest_ppPredicate[i] = c.adopt(native_ppPredicate[i], SD_COM_IF_ID3D11Predicate);
    p.ret = result;
    return;
}
case 26: { // ID3D11Device::CreateCounter
    auto pCounterDesc = c.read<D3D11_COUNTER_DESC>(p.args[0], c.array_count(1));
    const uint32_t count_ppCounter = c.array_count(1);
    auto guest_ppCounter = c.write<uint32_t>(p.args[1], count_ppCounter);
    if (guest_ppCounter) std::fill_n(guest_ppCounter, count_ppCounter, 0u);
    std::vector<ID3D11Counter*> native_ppCounter(count_ppCounter, nullptr);
    auto ppCounter = guest_ppCounter ? native_ppCounter.data() : nullptr;
    auto result = object->CreateCounter(pCounterDesc, ppCounter);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_ppCounter) for (uint32_t i=0; i<count_ppCounter; ++i) guest_ppCounter[i] = c.adopt(native_ppCounter[i], SD_COM_IF_ID3D11Counter);
    p.ret = result;
    return;
}
case 27: { // ID3D11Device::CreateDeferredContext
    auto ContextFlags = (UINT)p.args[0];
    const uint32_t count_ppDeferredContext = c.array_count(1);
    auto guest_ppDeferredContext = c.write<uint32_t>(p.args[1], count_ppDeferredContext);
    if (guest_ppDeferredContext) std::fill_n(guest_ppDeferredContext, count_ppDeferredContext, 0u);
    std::vector<ID3D11DeviceContext*> native_ppDeferredContext(count_ppDeferredContext, nullptr);
    auto ppDeferredContext = guest_ppDeferredContext ? native_ppDeferredContext.data() : nullptr;
    auto result = object->CreateDeferredContext(ContextFlags, ppDeferredContext);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_ppDeferredContext) for (uint32_t i=0; i<count_ppDeferredContext; ++i) guest_ppDeferredContext[i] = c.adopt(native_ppDeferredContext[i], SD_COM_IF_ID3D11DeviceContext);
    p.ret = result;
    return;
}
case 28: { // ID3D11Device::OpenSharedResource
    return c.unsupported(p, "ID3D11Device::OpenSharedResource");
}
case 29: { // ID3D11Device::CheckFormatSupport
    auto Format = (DXGI_FORMAT)p.args[0];
    auto pFormatSupport = c.write<UINT>(p.args[1], c.array_count(1));
    auto result = object->CheckFormatSupport(Format, pFormatSupport);
    p.ret = result;
    return;
}
case 30: { // ID3D11Device::CheckMultisampleQualityLevels
    auto Format = (DXGI_FORMAT)p.args[0];
    auto SampleCount = (UINT)p.args[1];
    auto pNumQualityLevels = c.write<UINT>(p.args[2], c.array_count(1));
    auto result = object->CheckMultisampleQualityLevels(Format, SampleCount, pNumQualityLevels);
    p.ret = result;
    return;
}
case 31: { // ID3D11Device::CheckCounterInfo
    auto pCounterInfo = c.write<D3D11_COUNTER_INFO>(p.args[0], c.array_count(1));
    object->CheckCounterInfo(pCounterInfo);
    p.ret = 0;
    return;
}
case 32: { // ID3D11Device::CheckCounter
    return custom_ID3D11Device_CheckCounter(c, object, p);
}
case 33: { // ID3D11Device::CheckFeatureSupport
    auto Feature = (D3D11_FEATURE)p.args[0];
    auto FeatureSupportDataSize = (UINT)p.args[2];
    auto pFeatureSupportData = c.write<unsigned char>(p.args[1], FeatureSupportDataSize);
    auto result = object->CheckFeatureSupport(Feature, pFeatureSupportData, FeatureSupportDataSize);
    p.ret = result;
    return;
}
case 34: { // ID3D11Device::GetPrivateData
    return custom_ID3D11Device_GetPrivateData(c, object, p);
}
case 35: { // ID3D11Device::SetPrivateData
    return custom_ID3D11Device_SetPrivateData(c, object, p);
}
case 36: { // ID3D11Device::SetPrivateDataInterface
    return custom_ID3D11Device_SetPrivateDataInterface(c, object, p);
}
case 37: { // ID3D11Device::GetFeatureLevel
    auto result = object->GetFeatureLevel();
    p.ret = result;
    return;
}
case 38: { // ID3D11Device::GetCreationFlags
    auto result = object->GetCreationFlags();
    p.ret = result;
    return;
}
case 39: { // ID3D11Device::GetDeviceRemovedReason
    auto result = object->GetDeviceRemovedReason();
    p.ret = result;
    return;
}
case 40: { // ID3D11Device::GetImmediateContext
    const uint32_t count_ppImmediateContext = c.array_count(1);
    auto guest_ppImmediateContext = c.write<uint32_t>(p.args[0], count_ppImmediateContext);
    if (guest_ppImmediateContext) std::fill_n(guest_ppImmediateContext, count_ppImmediateContext, 0u);
    std::vector<ID3D11DeviceContext*> native_ppImmediateContext(count_ppImmediateContext, nullptr);
    auto ppImmediateContext = guest_ppImmediateContext ? native_ppImmediateContext.data() : nullptr;
    object->GetImmediateContext(ppImmediateContext);
    if (guest_ppImmediateContext) for (uint32_t i=0; i<count_ppImmediateContext; ++i) guest_ppImmediateContext[i] = c.adopt(native_ppImmediateContext[i], SD_COM_IF_ID3D11DeviceContext);
    p.ret = 0;
    return;
}
case 41: { // ID3D11Device::SetExceptionMode
    auto RaiseFlags = (UINT)p.args[0];
    auto result = object->SetExceptionMode(RaiseFlags);
    p.ret = result;
    return;
}
case 42: { // ID3D11Device::GetExceptionMode
    auto result = object->GetExceptionMode();
    p.ret = result;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11DeviceChild: {
    auto object = c.object<ID3D11DeviceChild>(p.object, SD_COM_IF_ID3D11DeviceChild);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11DeviceChild::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11DeviceChild::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11DeviceChild::Release
    return c.Release(p);
}
case 3: { // ID3D11DeviceChild::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11DeviceChild::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11DeviceChild::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11DeviceChild::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11DeviceContext: {
    auto object = c.object<ID3D11DeviceContext>(p.object, SD_COM_IF_ID3D11DeviceContext);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11DeviceContext::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11DeviceContext::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11DeviceContext::Release
    return c.Release(p);
}
case 3: { // ID3D11DeviceContext::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11DeviceContext::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11DeviceContext::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11DeviceContext::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
case 7: { // ID3D11DeviceContext::VSSetConstantBuffers
    auto StartSlot = (UINT)p.args[0];
    auto NumBuffers = (UINT)p.args[1];
    const uint32_t count_ppConstantBuffers = c.array_count(NumBuffers);
    auto tokens_ppConstantBuffers = c.read<uint32_t>(p.args[2], count_ppConstantBuffers);
    std::vector<ID3D11Buffer*> native_ppConstantBuffers(tokens_ppConstantBuffers ? count_ppConstantBuffers : 0);
    for (uint32_t i=0; i<native_ppConstantBuffers.size(); ++i) native_ppConstantBuffers[i] = c.object<ID3D11Buffer>(tokens_ppConstantBuffers[i], SD_COM_IF_ID3D11Buffer);
    auto ppConstantBuffers = tokens_ppConstantBuffers ? native_ppConstantBuffers.data() : nullptr;
    object->VSSetConstantBuffers(StartSlot, NumBuffers, ppConstantBuffers);
    p.ret = 0;
    return;
}
case 8: { // ID3D11DeviceContext::PSSetShaderResources
    auto StartSlot = (UINT)p.args[0];
    auto NumViews = (UINT)p.args[1];
    const uint32_t count_ppShaderResourceViews = c.array_count(NumViews);
    auto tokens_ppShaderResourceViews = c.read<uint32_t>(p.args[2], count_ppShaderResourceViews);
    std::vector<ID3D11ShaderResourceView*> native_ppShaderResourceViews(tokens_ppShaderResourceViews ? count_ppShaderResourceViews : 0);
    for (uint32_t i=0; i<native_ppShaderResourceViews.size(); ++i) native_ppShaderResourceViews[i] = c.object<ID3D11ShaderResourceView>(tokens_ppShaderResourceViews[i], SD_COM_IF_ID3D11ShaderResourceView);
    auto ppShaderResourceViews = tokens_ppShaderResourceViews ? native_ppShaderResourceViews.data() : nullptr;
    object->PSSetShaderResources(StartSlot, NumViews, ppShaderResourceViews);
    p.ret = 0;
    return;
}
case 9: { // ID3D11DeviceContext::PSSetShader
    auto NumClassInstances = (UINT)p.args[2];
    auto pPixelShader = c.object<ID3D11PixelShader>(p.args[0], SD_COM_IF_ID3D11PixelShader);
    const uint32_t count_ppClassInstances = c.array_count(NumClassInstances);
    auto tokens_ppClassInstances = c.read<uint32_t>(p.args[1], count_ppClassInstances);
    std::vector<ID3D11ClassInstance*> native_ppClassInstances(tokens_ppClassInstances ? count_ppClassInstances : 0);
    for (uint32_t i=0; i<native_ppClassInstances.size(); ++i) native_ppClassInstances[i] = c.object<ID3D11ClassInstance>(tokens_ppClassInstances[i], SD_COM_IF_ID3D11ClassInstance);
    auto ppClassInstances = tokens_ppClassInstances ? native_ppClassInstances.data() : nullptr;
    object->PSSetShader(pPixelShader, ppClassInstances, NumClassInstances);
    p.ret = 0;
    return;
}
case 10: { // ID3D11DeviceContext::PSSetSamplers
    auto StartSlot = (UINT)p.args[0];
    auto NumSamplers = (UINT)p.args[1];
    const uint32_t count_ppSamplers = c.array_count(NumSamplers);
    auto tokens_ppSamplers = c.read<uint32_t>(p.args[2], count_ppSamplers);
    std::vector<ID3D11SamplerState*> native_ppSamplers(tokens_ppSamplers ? count_ppSamplers : 0);
    for (uint32_t i=0; i<native_ppSamplers.size(); ++i) native_ppSamplers[i] = c.object<ID3D11SamplerState>(tokens_ppSamplers[i], SD_COM_IF_ID3D11SamplerState);
    auto ppSamplers = tokens_ppSamplers ? native_ppSamplers.data() : nullptr;
    object->PSSetSamplers(StartSlot, NumSamplers, ppSamplers);
    p.ret = 0;
    return;
}
case 11: { // ID3D11DeviceContext::VSSetShader
    auto NumClassInstances = (UINT)p.args[2];
    auto pVertexShader = c.object<ID3D11VertexShader>(p.args[0], SD_COM_IF_ID3D11VertexShader);
    const uint32_t count_ppClassInstances = c.array_count(NumClassInstances);
    auto tokens_ppClassInstances = c.read<uint32_t>(p.args[1], count_ppClassInstances);
    std::vector<ID3D11ClassInstance*> native_ppClassInstances(tokens_ppClassInstances ? count_ppClassInstances : 0);
    for (uint32_t i=0; i<native_ppClassInstances.size(); ++i) native_ppClassInstances[i] = c.object<ID3D11ClassInstance>(tokens_ppClassInstances[i], SD_COM_IF_ID3D11ClassInstance);
    auto ppClassInstances = tokens_ppClassInstances ? native_ppClassInstances.data() : nullptr;
    object->VSSetShader(pVertexShader, ppClassInstances, NumClassInstances);
    p.ret = 0;
    return;
}
case 12: { // ID3D11DeviceContext::DrawIndexed
    auto IndexCount = (UINT)p.args[0];
    auto StartIndexLocation = (UINT)p.args[1];
    auto BaseVertexLocation = (INT)p.args[2];
    ++c.draws;
    object->DrawIndexed(IndexCount, StartIndexLocation, BaseVertexLocation);
    p.ret = 0;
    return;
}
case 13: { // ID3D11DeviceContext::Draw
    auto VertexCount = (UINT)p.args[0];
    auto StartVertexLocation = (UINT)p.args[1];
    ++c.draws;
    object->Draw(VertexCount, StartVertexLocation);
    p.ret = 0;
    return;
}
case 14: { // ID3D11DeviceContext::Map
    return custom_ID3D11DeviceContext_Map(c, object, p);
}
case 15: { // ID3D11DeviceContext::Unmap
    return custom_ID3D11DeviceContext_Unmap(c, object, p);
}
case 16: { // ID3D11DeviceContext::PSSetConstantBuffers
    auto StartSlot = (UINT)p.args[0];
    auto NumBuffers = (UINT)p.args[1];
    const uint32_t count_ppConstantBuffers = c.array_count(NumBuffers);
    auto tokens_ppConstantBuffers = c.read<uint32_t>(p.args[2], count_ppConstantBuffers);
    std::vector<ID3D11Buffer*> native_ppConstantBuffers(tokens_ppConstantBuffers ? count_ppConstantBuffers : 0);
    for (uint32_t i=0; i<native_ppConstantBuffers.size(); ++i) native_ppConstantBuffers[i] = c.object<ID3D11Buffer>(tokens_ppConstantBuffers[i], SD_COM_IF_ID3D11Buffer);
    auto ppConstantBuffers = tokens_ppConstantBuffers ? native_ppConstantBuffers.data() : nullptr;
    object->PSSetConstantBuffers(StartSlot, NumBuffers, ppConstantBuffers);
    p.ret = 0;
    return;
}
case 17: { // ID3D11DeviceContext::IASetInputLayout
    auto pInputLayout = c.object<ID3D11InputLayout>(p.args[0], SD_COM_IF_ID3D11InputLayout);
    object->IASetInputLayout(pInputLayout);
    p.ret = 0;
    return;
}
case 18: { // ID3D11DeviceContext::IASetVertexBuffers
    auto StartSlot = (UINT)p.args[0];
    auto NumBuffers = (UINT)p.args[1];
    auto pStrides = c.read<UINT>(p.args[3], c.array_count(NumBuffers));
    auto pOffsets = c.read<UINT>(p.args[4], c.array_count(NumBuffers));
    const uint32_t count_ppVertexBuffers = c.array_count(NumBuffers);
    auto tokens_ppVertexBuffers = c.read<uint32_t>(p.args[2], count_ppVertexBuffers);
    std::vector<ID3D11Buffer*> native_ppVertexBuffers(tokens_ppVertexBuffers ? count_ppVertexBuffers : 0);
    for (uint32_t i=0; i<native_ppVertexBuffers.size(); ++i) native_ppVertexBuffers[i] = c.object<ID3D11Buffer>(tokens_ppVertexBuffers[i], SD_COM_IF_ID3D11Buffer);
    auto ppVertexBuffers = tokens_ppVertexBuffers ? native_ppVertexBuffers.data() : nullptr;
    object->IASetVertexBuffers(StartSlot, NumBuffers, ppVertexBuffers, pStrides, pOffsets);
    p.ret = 0;
    return;
}
case 19: { // ID3D11DeviceContext::IASetIndexBuffer
    auto Format = (DXGI_FORMAT)p.args[1];
    auto Offset = (UINT)p.args[2];
    auto pIndexBuffer = c.object<ID3D11Buffer>(p.args[0], SD_COM_IF_ID3D11Buffer);
    object->IASetIndexBuffer(pIndexBuffer, Format, Offset);
    p.ret = 0;
    return;
}
case 20: { // ID3D11DeviceContext::DrawIndexedInstanced
    auto IndexCountPerInstance = (UINT)p.args[0];
    auto InstanceCount = (UINT)p.args[1];
    auto StartIndexLocation = (UINT)p.args[2];
    auto BaseVertexLocation = (INT)p.args[3];
    auto StartInstanceLocation = (UINT)p.args[4];
    ++c.draws;
    object->DrawIndexedInstanced(IndexCountPerInstance, InstanceCount, StartIndexLocation, BaseVertexLocation, StartInstanceLocation);
    p.ret = 0;
    return;
}
case 21: { // ID3D11DeviceContext::DrawInstanced
    auto VertexCountPerInstance = (UINT)p.args[0];
    auto InstanceCount = (UINT)p.args[1];
    auto StartVertexLocation = (UINT)p.args[2];
    auto StartInstanceLocation = (UINT)p.args[3];
    ++c.draws;
    object->DrawInstanced(VertexCountPerInstance, InstanceCount, StartVertexLocation, StartInstanceLocation);
    p.ret = 0;
    return;
}
case 22: { // ID3D11DeviceContext::GSSetConstantBuffers
    auto StartSlot = (UINT)p.args[0];
    auto NumBuffers = (UINT)p.args[1];
    const uint32_t count_ppConstantBuffers = c.array_count(NumBuffers);
    auto tokens_ppConstantBuffers = c.read<uint32_t>(p.args[2], count_ppConstantBuffers);
    std::vector<ID3D11Buffer*> native_ppConstantBuffers(tokens_ppConstantBuffers ? count_ppConstantBuffers : 0);
    for (uint32_t i=0; i<native_ppConstantBuffers.size(); ++i) native_ppConstantBuffers[i] = c.object<ID3D11Buffer>(tokens_ppConstantBuffers[i], SD_COM_IF_ID3D11Buffer);
    auto ppConstantBuffers = tokens_ppConstantBuffers ? native_ppConstantBuffers.data() : nullptr;
    object->GSSetConstantBuffers(StartSlot, NumBuffers, ppConstantBuffers);
    p.ret = 0;
    return;
}
case 23: { // ID3D11DeviceContext::GSSetShader
    auto NumClassInstances = (UINT)p.args[2];
    auto pShader = c.object<ID3D11GeometryShader>(p.args[0], SD_COM_IF_ID3D11GeometryShader);
    const uint32_t count_ppClassInstances = c.array_count(NumClassInstances);
    auto tokens_ppClassInstances = c.read<uint32_t>(p.args[1], count_ppClassInstances);
    std::vector<ID3D11ClassInstance*> native_ppClassInstances(tokens_ppClassInstances ? count_ppClassInstances : 0);
    for (uint32_t i=0; i<native_ppClassInstances.size(); ++i) native_ppClassInstances[i] = c.object<ID3D11ClassInstance>(tokens_ppClassInstances[i], SD_COM_IF_ID3D11ClassInstance);
    auto ppClassInstances = tokens_ppClassInstances ? native_ppClassInstances.data() : nullptr;
    object->GSSetShader(pShader, ppClassInstances, NumClassInstances);
    p.ret = 0;
    return;
}
case 24: { // ID3D11DeviceContext::IASetPrimitiveTopology
    auto Topology = (D3D11_PRIMITIVE_TOPOLOGY)p.args[0];
    object->IASetPrimitiveTopology(Topology);
    p.ret = 0;
    return;
}
case 25: { // ID3D11DeviceContext::VSSetShaderResources
    auto StartSlot = (UINT)p.args[0];
    auto NumViews = (UINT)p.args[1];
    const uint32_t count_ppShaderResourceViews = c.array_count(NumViews);
    auto tokens_ppShaderResourceViews = c.read<uint32_t>(p.args[2], count_ppShaderResourceViews);
    std::vector<ID3D11ShaderResourceView*> native_ppShaderResourceViews(tokens_ppShaderResourceViews ? count_ppShaderResourceViews : 0);
    for (uint32_t i=0; i<native_ppShaderResourceViews.size(); ++i) native_ppShaderResourceViews[i] = c.object<ID3D11ShaderResourceView>(tokens_ppShaderResourceViews[i], SD_COM_IF_ID3D11ShaderResourceView);
    auto ppShaderResourceViews = tokens_ppShaderResourceViews ? native_ppShaderResourceViews.data() : nullptr;
    object->VSSetShaderResources(StartSlot, NumViews, ppShaderResourceViews);
    p.ret = 0;
    return;
}
case 26: { // ID3D11DeviceContext::VSSetSamplers
    auto StartSlot = (UINT)p.args[0];
    auto NumSamplers = (UINT)p.args[1];
    const uint32_t count_ppSamplers = c.array_count(NumSamplers);
    auto tokens_ppSamplers = c.read<uint32_t>(p.args[2], count_ppSamplers);
    std::vector<ID3D11SamplerState*> native_ppSamplers(tokens_ppSamplers ? count_ppSamplers : 0);
    for (uint32_t i=0; i<native_ppSamplers.size(); ++i) native_ppSamplers[i] = c.object<ID3D11SamplerState>(tokens_ppSamplers[i], SD_COM_IF_ID3D11SamplerState);
    auto ppSamplers = tokens_ppSamplers ? native_ppSamplers.data() : nullptr;
    object->VSSetSamplers(StartSlot, NumSamplers, ppSamplers);
    p.ret = 0;
    return;
}
case 27: { // ID3D11DeviceContext::Begin
    auto pAsync = c.object<ID3D11Asynchronous>(p.args[0], SD_COM_IF_ID3D11Asynchronous);
    object->Begin(pAsync);
    p.ret = 0;
    return;
}
case 28: { // ID3D11DeviceContext::End
    auto pAsync = c.object<ID3D11Asynchronous>(p.args[0], SD_COM_IF_ID3D11Asynchronous);
    object->End(pAsync);
    p.ret = 0;
    return;
}
case 29: { // ID3D11DeviceContext::GetData
    auto DataSize = (UINT)p.args[2];
    auto GetDataFlags = (UINT)p.args[3];
    auto pAsync = c.object<ID3D11Asynchronous>(p.args[0], SD_COM_IF_ID3D11Asynchronous);
    auto pData = c.write<unsigned char>(p.args[1], DataSize);
    auto result = object->GetData(pAsync, pData, DataSize, GetDataFlags);
    p.ret = result;
    return;
}
case 30: { // ID3D11DeviceContext::SetPredication
    auto PredicateValue = (WINBOOL)p.args[1];
    auto pPredicate = c.object<ID3D11Predicate>(p.args[0], SD_COM_IF_ID3D11Predicate);
    object->SetPredication(pPredicate, PredicateValue);
    p.ret = 0;
    return;
}
case 31: { // ID3D11DeviceContext::GSSetShaderResources
    auto StartSlot = (UINT)p.args[0];
    auto NumViews = (UINT)p.args[1];
    const uint32_t count_ppShaderResourceViews = c.array_count(NumViews);
    auto tokens_ppShaderResourceViews = c.read<uint32_t>(p.args[2], count_ppShaderResourceViews);
    std::vector<ID3D11ShaderResourceView*> native_ppShaderResourceViews(tokens_ppShaderResourceViews ? count_ppShaderResourceViews : 0);
    for (uint32_t i=0; i<native_ppShaderResourceViews.size(); ++i) native_ppShaderResourceViews[i] = c.object<ID3D11ShaderResourceView>(tokens_ppShaderResourceViews[i], SD_COM_IF_ID3D11ShaderResourceView);
    auto ppShaderResourceViews = tokens_ppShaderResourceViews ? native_ppShaderResourceViews.data() : nullptr;
    object->GSSetShaderResources(StartSlot, NumViews, ppShaderResourceViews);
    p.ret = 0;
    return;
}
case 32: { // ID3D11DeviceContext::GSSetSamplers
    auto StartSlot = (UINT)p.args[0];
    auto NumSamplers = (UINT)p.args[1];
    const uint32_t count_ppSamplers = c.array_count(NumSamplers);
    auto tokens_ppSamplers = c.read<uint32_t>(p.args[2], count_ppSamplers);
    std::vector<ID3D11SamplerState*> native_ppSamplers(tokens_ppSamplers ? count_ppSamplers : 0);
    for (uint32_t i=0; i<native_ppSamplers.size(); ++i) native_ppSamplers[i] = c.object<ID3D11SamplerState>(tokens_ppSamplers[i], SD_COM_IF_ID3D11SamplerState);
    auto ppSamplers = tokens_ppSamplers ? native_ppSamplers.data() : nullptr;
    object->GSSetSamplers(StartSlot, NumSamplers, ppSamplers);
    p.ret = 0;
    return;
}
case 33: { // ID3D11DeviceContext::OMSetRenderTargets
    auto NumViews = (UINT)p.args[0];
    const uint32_t count_ppRenderTargetViews = c.array_count(NumViews);
    auto tokens_ppRenderTargetViews = c.read<uint32_t>(p.args[1], count_ppRenderTargetViews);
    std::vector<ID3D11RenderTargetView*> native_ppRenderTargetViews(tokens_ppRenderTargetViews ? count_ppRenderTargetViews : 0);
    for (uint32_t i=0; i<native_ppRenderTargetViews.size(); ++i) native_ppRenderTargetViews[i] = c.object<ID3D11RenderTargetView>(tokens_ppRenderTargetViews[i], SD_COM_IF_ID3D11RenderTargetView);
    auto ppRenderTargetViews = tokens_ppRenderTargetViews ? native_ppRenderTargetViews.data() : nullptr;
    auto pDepthStencilView = c.object<ID3D11DepthStencilView>(p.args[2], SD_COM_IF_ID3D11DepthStencilView);
    object->OMSetRenderTargets(NumViews, ppRenderTargetViews, pDepthStencilView);
    p.ret = 0;
    return;
}
case 34: { // ID3D11DeviceContext::OMSetRenderTargetsAndUnorderedAccessViews
    auto NumRTVs = (UINT)p.args[0];
    auto UAVStartSlot = (UINT)p.args[3];
    auto NumUAVs = (UINT)p.args[4];
    auto pUAVInitialCounts = c.read<UINT>(p.args[6], c.keep_array_count(NumUAVs));
    const uint32_t count_ppRenderTargetViews = c.keep_array_count(NumRTVs);
    auto tokens_ppRenderTargetViews = c.read<uint32_t>(p.args[1], count_ppRenderTargetViews);
    std::vector<ID3D11RenderTargetView*> native_ppRenderTargetViews(tokens_ppRenderTargetViews ? count_ppRenderTargetViews : 0);
    for (uint32_t i=0; i<native_ppRenderTargetViews.size(); ++i) native_ppRenderTargetViews[i] = c.object<ID3D11RenderTargetView>(tokens_ppRenderTargetViews[i], SD_COM_IF_ID3D11RenderTargetView);
    auto ppRenderTargetViews = tokens_ppRenderTargetViews ? native_ppRenderTargetViews.data() : nullptr;
    auto pDepthStencilView = c.object<ID3D11DepthStencilView>(p.args[2], SD_COM_IF_ID3D11DepthStencilView);
    const uint32_t count_ppUnorderedAccessViews = c.keep_array_count(NumUAVs);
    auto tokens_ppUnorderedAccessViews = c.read<uint32_t>(p.args[5], count_ppUnorderedAccessViews);
    std::vector<ID3D11UnorderedAccessView*> native_ppUnorderedAccessViews(tokens_ppUnorderedAccessViews ? count_ppUnorderedAccessViews : 0);
    for (uint32_t i=0; i<native_ppUnorderedAccessViews.size(); ++i) native_ppUnorderedAccessViews[i] = c.object<ID3D11UnorderedAccessView>(tokens_ppUnorderedAccessViews[i], SD_COM_IF_ID3D11UnorderedAccessView);
    auto ppUnorderedAccessViews = tokens_ppUnorderedAccessViews ? native_ppUnorderedAccessViews.data() : nullptr;
    object->OMSetRenderTargetsAndUnorderedAccessViews(NumRTVs, ppRenderTargetViews, pDepthStencilView, UAVStartSlot, NumUAVs, ppUnorderedAccessViews, pUAVInitialCounts);
    p.ret = 0;
    return;
}
case 35: { // ID3D11DeviceContext::OMSetBlendState
    auto SampleMask = (UINT)p.args[2];
    auto pBlendState = c.object<ID3D11BlendState>(p.args[0], SD_COM_IF_ID3D11BlendState);
    auto BlendFactor = c.read<FLOAT>(p.args[1], c.array_count(4));
    object->OMSetBlendState(pBlendState, BlendFactor, SampleMask);
    p.ret = 0;
    return;
}
case 36: { // ID3D11DeviceContext::OMSetDepthStencilState
    auto StencilRef = (UINT)p.args[1];
    auto pDepthStencilState = c.object<ID3D11DepthStencilState>(p.args[0], SD_COM_IF_ID3D11DepthStencilState);
    object->OMSetDepthStencilState(pDepthStencilState, StencilRef);
    p.ret = 0;
    return;
}
case 37: { // ID3D11DeviceContext::SOSetTargets
    auto NumBuffers = (UINT)p.args[0];
    auto pOffsets = c.read<UINT>(p.args[2], c.array_count(NumBuffers));
    const uint32_t count_ppSOTargets = c.array_count(NumBuffers);
    auto tokens_ppSOTargets = c.read<uint32_t>(p.args[1], count_ppSOTargets);
    std::vector<ID3D11Buffer*> native_ppSOTargets(tokens_ppSOTargets ? count_ppSOTargets : 0);
    for (uint32_t i=0; i<native_ppSOTargets.size(); ++i) native_ppSOTargets[i] = c.object<ID3D11Buffer>(tokens_ppSOTargets[i], SD_COM_IF_ID3D11Buffer);
    auto ppSOTargets = tokens_ppSOTargets ? native_ppSOTargets.data() : nullptr;
    object->SOSetTargets(NumBuffers, ppSOTargets, pOffsets);
    p.ret = 0;
    return;
}
case 38: { // ID3D11DeviceContext::DrawAuto
    ++c.draws;
    object->DrawAuto();
    p.ret = 0;
    return;
}
case 39: { // ID3D11DeviceContext::DrawIndexedInstancedIndirect
    auto AlignedByteOffsetForArgs = (UINT)p.args[1];
    auto pBufferForArgs = c.object<ID3D11Buffer>(p.args[0], SD_COM_IF_ID3D11Buffer);
    ++c.draws;
    object->DrawIndexedInstancedIndirect(pBufferForArgs, AlignedByteOffsetForArgs);
    p.ret = 0;
    return;
}
case 40: { // ID3D11DeviceContext::DrawInstancedIndirect
    auto AlignedByteOffsetForArgs = (UINT)p.args[1];
    auto pBufferForArgs = c.object<ID3D11Buffer>(p.args[0], SD_COM_IF_ID3D11Buffer);
    ++c.draws;
    object->DrawInstancedIndirect(pBufferForArgs, AlignedByteOffsetForArgs);
    p.ret = 0;
    return;
}
case 41: { // ID3D11DeviceContext::Dispatch
    auto ThreadGroupCountX = (UINT)p.args[0];
    auto ThreadGroupCountY = (UINT)p.args[1];
    auto ThreadGroupCountZ = (UINT)p.args[2];
    object->Dispatch(ThreadGroupCountX, ThreadGroupCountY, ThreadGroupCountZ);
    p.ret = 0;
    return;
}
case 42: { // ID3D11DeviceContext::DispatchIndirect
    auto AlignedByteOffsetForArgs = (UINT)p.args[1];
    auto pBufferForArgs = c.object<ID3D11Buffer>(p.args[0], SD_COM_IF_ID3D11Buffer);
    object->DispatchIndirect(pBufferForArgs, AlignedByteOffsetForArgs);
    p.ret = 0;
    return;
}
case 43: { // ID3D11DeviceContext::RSSetState
    auto pRasterizerState = c.object<ID3D11RasterizerState>(p.args[0], SD_COM_IF_ID3D11RasterizerState);
    object->RSSetState(pRasterizerState);
    p.ret = 0;
    return;
}
case 44: { // ID3D11DeviceContext::RSSetViewports
    auto NumViewports = (UINT)p.args[0];
    auto pViewports = c.read<D3D11_VIEWPORT>(p.args[1], c.array_count(NumViewports));
    object->RSSetViewports(NumViewports, pViewports);
    p.ret = 0;
    return;
}
case 45: { // ID3D11DeviceContext::RSSetScissorRects
    auto NumRects = (UINT)p.args[0];
    auto pRects = c.read<D3D11_RECT>(p.args[1], c.array_count(NumRects));
    object->RSSetScissorRects(NumRects, pRects);
    p.ret = 0;
    return;
}
case 46: { // ID3D11DeviceContext::CopySubresourceRegion
    auto DstSubresource = (UINT)p.args[1];
    auto DstX = (UINT)p.args[2];
    auto DstY = (UINT)p.args[3];
    auto DstZ = (UINT)p.args[4];
    auto SrcSubresource = (UINT)p.args[6];
    auto pDstResource = c.object<ID3D11Resource>(p.args[0], SD_COM_IF_ID3D11Resource);
    auto pSrcResource = c.object<ID3D11Resource>(p.args[5], SD_COM_IF_ID3D11Resource);
    auto pSrcBox = c.read<D3D11_BOX>(p.args[7], c.array_count(1));
    object->CopySubresourceRegion(pDstResource, DstSubresource, DstX, DstY, DstZ, pSrcResource, SrcSubresource, pSrcBox);
    p.ret = 0;
    return;
}
case 47: { // ID3D11DeviceContext::CopyResource
    auto pDstResource = c.object<ID3D11Resource>(p.args[0], SD_COM_IF_ID3D11Resource);
    auto pSrcResource = c.object<ID3D11Resource>(p.args[1], SD_COM_IF_ID3D11Resource);
    object->CopyResource(pDstResource, pSrcResource);
    p.ret = 0;
    return;
}
case 48: { // ID3D11DeviceContext::UpdateSubresource
    return custom_ID3D11DeviceContext_UpdateSubresource(c, object, p);
}
case 49: { // ID3D11DeviceContext::CopyStructureCount
    auto DstAlignedByteOffset = (UINT)p.args[1];
    auto pDstBuffer = c.object<ID3D11Buffer>(p.args[0], SD_COM_IF_ID3D11Buffer);
    auto pSrcView = c.object<ID3D11UnorderedAccessView>(p.args[2], SD_COM_IF_ID3D11UnorderedAccessView);
    object->CopyStructureCount(pDstBuffer, DstAlignedByteOffset, pSrcView);
    p.ret = 0;
    return;
}
case 50: { // ID3D11DeviceContext::ClearRenderTargetView
    auto pRenderTargetView = c.object<ID3D11RenderTargetView>(p.args[0], SD_COM_IF_ID3D11RenderTargetView);
    auto ColorRGBA = c.read<FLOAT>(p.args[1], c.array_count(4));
    object->ClearRenderTargetView(pRenderTargetView, ColorRGBA);
    p.ret = 0;
    return;
}
case 51: { // ID3D11DeviceContext::ClearUnorderedAccessViewUint
    auto Values = c.read<UINT>(p.args[1], c.array_count(4));
    auto pUnorderedAccessView = c.object<ID3D11UnorderedAccessView>(p.args[0], SD_COM_IF_ID3D11UnorderedAccessView);
    object->ClearUnorderedAccessViewUint(pUnorderedAccessView, Values);
    p.ret = 0;
    return;
}
case 52: { // ID3D11DeviceContext::ClearUnorderedAccessViewFloat
    auto pUnorderedAccessView = c.object<ID3D11UnorderedAccessView>(p.args[0], SD_COM_IF_ID3D11UnorderedAccessView);
    auto Values = c.read<FLOAT>(p.args[1], c.array_count(4));
    object->ClearUnorderedAccessViewFloat(pUnorderedAccessView, Values);
    p.ret = 0;
    return;
}
case 53: { // ID3D11DeviceContext::ClearDepthStencilView
    auto ClearFlags = (UINT)p.args[1];
    auto Depth = bits_float(p.args[2]);
    auto Stencil = (UINT8)p.args[3];
    auto pDepthStencilView = c.object<ID3D11DepthStencilView>(p.args[0], SD_COM_IF_ID3D11DepthStencilView);
    object->ClearDepthStencilView(pDepthStencilView, ClearFlags, Depth, Stencil);
    p.ret = 0;
    return;
}
case 54: { // ID3D11DeviceContext::GenerateMips
    auto pShaderResourceView = c.object<ID3D11ShaderResourceView>(p.args[0], SD_COM_IF_ID3D11ShaderResourceView);
    object->GenerateMips(pShaderResourceView);
    p.ret = 0;
    return;
}
case 55: { // ID3D11DeviceContext::SetResourceMinLOD
    auto MinLOD = bits_float(p.args[1]);
    auto pResource = c.object<ID3D11Resource>(p.args[0], SD_COM_IF_ID3D11Resource);
    object->SetResourceMinLOD(pResource, MinLOD);
    p.ret = 0;
    return;
}
case 56: { // ID3D11DeviceContext::GetResourceMinLOD
    auto pResource = c.object<ID3D11Resource>(p.args[0], SD_COM_IF_ID3D11Resource);
    auto result = object->GetResourceMinLOD(pResource);
    p.ret = bits_float(result);
    return;
}
case 57: { // ID3D11DeviceContext::ResolveSubresource
    auto DstSubresource = (UINT)p.args[1];
    auto SrcSubresource = (UINT)p.args[3];
    auto Format = (DXGI_FORMAT)p.args[4];
    auto pDstResource = c.object<ID3D11Resource>(p.args[0], SD_COM_IF_ID3D11Resource);
    auto pSrcResource = c.object<ID3D11Resource>(p.args[2], SD_COM_IF_ID3D11Resource);
    object->ResolveSubresource(pDstResource, DstSubresource, pSrcResource, SrcSubresource, Format);
    p.ret = 0;
    return;
}
case 58: { // ID3D11DeviceContext::ExecuteCommandList
    auto RestoreContextState = (WINBOOL)p.args[1];
    auto pCommandList = c.object<ID3D11CommandList>(p.args[0], SD_COM_IF_ID3D11CommandList);
    object->ExecuteCommandList(pCommandList, RestoreContextState);
    p.ret = 0;
    return;
}
case 59: { // ID3D11DeviceContext::HSSetShaderResources
    auto StartSlot = (UINT)p.args[0];
    auto NumViews = (UINT)p.args[1];
    const uint32_t count_ppShaderResourceViews = c.array_count(NumViews);
    auto tokens_ppShaderResourceViews = c.read<uint32_t>(p.args[2], count_ppShaderResourceViews);
    std::vector<ID3D11ShaderResourceView*> native_ppShaderResourceViews(tokens_ppShaderResourceViews ? count_ppShaderResourceViews : 0);
    for (uint32_t i=0; i<native_ppShaderResourceViews.size(); ++i) native_ppShaderResourceViews[i] = c.object<ID3D11ShaderResourceView>(tokens_ppShaderResourceViews[i], SD_COM_IF_ID3D11ShaderResourceView);
    auto ppShaderResourceViews = tokens_ppShaderResourceViews ? native_ppShaderResourceViews.data() : nullptr;
    object->HSSetShaderResources(StartSlot, NumViews, ppShaderResourceViews);
    p.ret = 0;
    return;
}
case 60: { // ID3D11DeviceContext::HSSetShader
    auto NumClassInstances = (UINT)p.args[2];
    auto pHullShader = c.object<ID3D11HullShader>(p.args[0], SD_COM_IF_ID3D11HullShader);
    const uint32_t count_ppClassInstances = c.array_count(NumClassInstances);
    auto tokens_ppClassInstances = c.read<uint32_t>(p.args[1], count_ppClassInstances);
    std::vector<ID3D11ClassInstance*> native_ppClassInstances(tokens_ppClassInstances ? count_ppClassInstances : 0);
    for (uint32_t i=0; i<native_ppClassInstances.size(); ++i) native_ppClassInstances[i] = c.object<ID3D11ClassInstance>(tokens_ppClassInstances[i], SD_COM_IF_ID3D11ClassInstance);
    auto ppClassInstances = tokens_ppClassInstances ? native_ppClassInstances.data() : nullptr;
    object->HSSetShader(pHullShader, ppClassInstances, NumClassInstances);
    p.ret = 0;
    return;
}
case 61: { // ID3D11DeviceContext::HSSetSamplers
    auto StartSlot = (UINT)p.args[0];
    auto NumSamplers = (UINT)p.args[1];
    const uint32_t count_ppSamplers = c.array_count(NumSamplers);
    auto tokens_ppSamplers = c.read<uint32_t>(p.args[2], count_ppSamplers);
    std::vector<ID3D11SamplerState*> native_ppSamplers(tokens_ppSamplers ? count_ppSamplers : 0);
    for (uint32_t i=0; i<native_ppSamplers.size(); ++i) native_ppSamplers[i] = c.object<ID3D11SamplerState>(tokens_ppSamplers[i], SD_COM_IF_ID3D11SamplerState);
    auto ppSamplers = tokens_ppSamplers ? native_ppSamplers.data() : nullptr;
    object->HSSetSamplers(StartSlot, NumSamplers, ppSamplers);
    p.ret = 0;
    return;
}
case 62: { // ID3D11DeviceContext::HSSetConstantBuffers
    auto StartSlot = (UINT)p.args[0];
    auto NumBuffers = (UINT)p.args[1];
    const uint32_t count_ppConstantBuffers = c.array_count(NumBuffers);
    auto tokens_ppConstantBuffers = c.read<uint32_t>(p.args[2], count_ppConstantBuffers);
    std::vector<ID3D11Buffer*> native_ppConstantBuffers(tokens_ppConstantBuffers ? count_ppConstantBuffers : 0);
    for (uint32_t i=0; i<native_ppConstantBuffers.size(); ++i) native_ppConstantBuffers[i] = c.object<ID3D11Buffer>(tokens_ppConstantBuffers[i], SD_COM_IF_ID3D11Buffer);
    auto ppConstantBuffers = tokens_ppConstantBuffers ? native_ppConstantBuffers.data() : nullptr;
    object->HSSetConstantBuffers(StartSlot, NumBuffers, ppConstantBuffers);
    p.ret = 0;
    return;
}
case 63: { // ID3D11DeviceContext::DSSetShaderResources
    auto StartSlot = (UINT)p.args[0];
    auto NumViews = (UINT)p.args[1];
    const uint32_t count_ppShaderResourceViews = c.array_count(NumViews);
    auto tokens_ppShaderResourceViews = c.read<uint32_t>(p.args[2], count_ppShaderResourceViews);
    std::vector<ID3D11ShaderResourceView*> native_ppShaderResourceViews(tokens_ppShaderResourceViews ? count_ppShaderResourceViews : 0);
    for (uint32_t i=0; i<native_ppShaderResourceViews.size(); ++i) native_ppShaderResourceViews[i] = c.object<ID3D11ShaderResourceView>(tokens_ppShaderResourceViews[i], SD_COM_IF_ID3D11ShaderResourceView);
    auto ppShaderResourceViews = tokens_ppShaderResourceViews ? native_ppShaderResourceViews.data() : nullptr;
    object->DSSetShaderResources(StartSlot, NumViews, ppShaderResourceViews);
    p.ret = 0;
    return;
}
case 64: { // ID3D11DeviceContext::DSSetShader
    auto NumClassInstances = (UINT)p.args[2];
    auto pDomainShader = c.object<ID3D11DomainShader>(p.args[0], SD_COM_IF_ID3D11DomainShader);
    const uint32_t count_ppClassInstances = c.array_count(NumClassInstances);
    auto tokens_ppClassInstances = c.read<uint32_t>(p.args[1], count_ppClassInstances);
    std::vector<ID3D11ClassInstance*> native_ppClassInstances(tokens_ppClassInstances ? count_ppClassInstances : 0);
    for (uint32_t i=0; i<native_ppClassInstances.size(); ++i) native_ppClassInstances[i] = c.object<ID3D11ClassInstance>(tokens_ppClassInstances[i], SD_COM_IF_ID3D11ClassInstance);
    auto ppClassInstances = tokens_ppClassInstances ? native_ppClassInstances.data() : nullptr;
    object->DSSetShader(pDomainShader, ppClassInstances, NumClassInstances);
    p.ret = 0;
    return;
}
case 65: { // ID3D11DeviceContext::DSSetSamplers
    auto StartSlot = (UINT)p.args[0];
    auto NumSamplers = (UINT)p.args[1];
    const uint32_t count_ppSamplers = c.array_count(NumSamplers);
    auto tokens_ppSamplers = c.read<uint32_t>(p.args[2], count_ppSamplers);
    std::vector<ID3D11SamplerState*> native_ppSamplers(tokens_ppSamplers ? count_ppSamplers : 0);
    for (uint32_t i=0; i<native_ppSamplers.size(); ++i) native_ppSamplers[i] = c.object<ID3D11SamplerState>(tokens_ppSamplers[i], SD_COM_IF_ID3D11SamplerState);
    auto ppSamplers = tokens_ppSamplers ? native_ppSamplers.data() : nullptr;
    object->DSSetSamplers(StartSlot, NumSamplers, ppSamplers);
    p.ret = 0;
    return;
}
case 66: { // ID3D11DeviceContext::DSSetConstantBuffers
    auto StartSlot = (UINT)p.args[0];
    auto NumBuffers = (UINT)p.args[1];
    const uint32_t count_ppConstantBuffers = c.array_count(NumBuffers);
    auto tokens_ppConstantBuffers = c.read<uint32_t>(p.args[2], count_ppConstantBuffers);
    std::vector<ID3D11Buffer*> native_ppConstantBuffers(tokens_ppConstantBuffers ? count_ppConstantBuffers : 0);
    for (uint32_t i=0; i<native_ppConstantBuffers.size(); ++i) native_ppConstantBuffers[i] = c.object<ID3D11Buffer>(tokens_ppConstantBuffers[i], SD_COM_IF_ID3D11Buffer);
    auto ppConstantBuffers = tokens_ppConstantBuffers ? native_ppConstantBuffers.data() : nullptr;
    object->DSSetConstantBuffers(StartSlot, NumBuffers, ppConstantBuffers);
    p.ret = 0;
    return;
}
case 67: { // ID3D11DeviceContext::CSSetShaderResources
    auto StartSlot = (UINT)p.args[0];
    auto NumViews = (UINT)p.args[1];
    const uint32_t count_ppShaderResourceViews = c.array_count(NumViews);
    auto tokens_ppShaderResourceViews = c.read<uint32_t>(p.args[2], count_ppShaderResourceViews);
    std::vector<ID3D11ShaderResourceView*> native_ppShaderResourceViews(tokens_ppShaderResourceViews ? count_ppShaderResourceViews : 0);
    for (uint32_t i=0; i<native_ppShaderResourceViews.size(); ++i) native_ppShaderResourceViews[i] = c.object<ID3D11ShaderResourceView>(tokens_ppShaderResourceViews[i], SD_COM_IF_ID3D11ShaderResourceView);
    auto ppShaderResourceViews = tokens_ppShaderResourceViews ? native_ppShaderResourceViews.data() : nullptr;
    object->CSSetShaderResources(StartSlot, NumViews, ppShaderResourceViews);
    p.ret = 0;
    return;
}
case 68: { // ID3D11DeviceContext::CSSetUnorderedAccessViews
    auto StartSlot = (UINT)p.args[0];
    auto NumUAVs = (UINT)p.args[1];
    auto pUAVInitialCounts = c.read<UINT>(p.args[3], c.array_count(NumUAVs));
    const uint32_t count_ppUnorderedAccessViews = c.array_count(NumUAVs);
    auto tokens_ppUnorderedAccessViews = c.read<uint32_t>(p.args[2], count_ppUnorderedAccessViews);
    std::vector<ID3D11UnorderedAccessView*> native_ppUnorderedAccessViews(tokens_ppUnorderedAccessViews ? count_ppUnorderedAccessViews : 0);
    for (uint32_t i=0; i<native_ppUnorderedAccessViews.size(); ++i) native_ppUnorderedAccessViews[i] = c.object<ID3D11UnorderedAccessView>(tokens_ppUnorderedAccessViews[i], SD_COM_IF_ID3D11UnorderedAccessView);
    auto ppUnorderedAccessViews = tokens_ppUnorderedAccessViews ? native_ppUnorderedAccessViews.data() : nullptr;
    object->CSSetUnorderedAccessViews(StartSlot, NumUAVs, ppUnorderedAccessViews, pUAVInitialCounts);
    p.ret = 0;
    return;
}
case 69: { // ID3D11DeviceContext::CSSetShader
    auto NumClassInstances = (UINT)p.args[2];
    auto pComputeShader = c.object<ID3D11ComputeShader>(p.args[0], SD_COM_IF_ID3D11ComputeShader);
    const uint32_t count_ppClassInstances = c.array_count(NumClassInstances);
    auto tokens_ppClassInstances = c.read<uint32_t>(p.args[1], count_ppClassInstances);
    std::vector<ID3D11ClassInstance*> native_ppClassInstances(tokens_ppClassInstances ? count_ppClassInstances : 0);
    for (uint32_t i=0; i<native_ppClassInstances.size(); ++i) native_ppClassInstances[i] = c.object<ID3D11ClassInstance>(tokens_ppClassInstances[i], SD_COM_IF_ID3D11ClassInstance);
    auto ppClassInstances = tokens_ppClassInstances ? native_ppClassInstances.data() : nullptr;
    object->CSSetShader(pComputeShader, ppClassInstances, NumClassInstances);
    p.ret = 0;
    return;
}
case 70: { // ID3D11DeviceContext::CSSetSamplers
    auto StartSlot = (UINT)p.args[0];
    auto NumSamplers = (UINT)p.args[1];
    const uint32_t count_ppSamplers = c.array_count(NumSamplers);
    auto tokens_ppSamplers = c.read<uint32_t>(p.args[2], count_ppSamplers);
    std::vector<ID3D11SamplerState*> native_ppSamplers(tokens_ppSamplers ? count_ppSamplers : 0);
    for (uint32_t i=0; i<native_ppSamplers.size(); ++i) native_ppSamplers[i] = c.object<ID3D11SamplerState>(tokens_ppSamplers[i], SD_COM_IF_ID3D11SamplerState);
    auto ppSamplers = tokens_ppSamplers ? native_ppSamplers.data() : nullptr;
    object->CSSetSamplers(StartSlot, NumSamplers, ppSamplers);
    p.ret = 0;
    return;
}
case 71: { // ID3D11DeviceContext::CSSetConstantBuffers
    auto StartSlot = (UINT)p.args[0];
    auto NumBuffers = (UINT)p.args[1];
    const uint32_t count_ppConstantBuffers = c.array_count(NumBuffers);
    auto tokens_ppConstantBuffers = c.read<uint32_t>(p.args[2], count_ppConstantBuffers);
    std::vector<ID3D11Buffer*> native_ppConstantBuffers(tokens_ppConstantBuffers ? count_ppConstantBuffers : 0);
    for (uint32_t i=0; i<native_ppConstantBuffers.size(); ++i) native_ppConstantBuffers[i] = c.object<ID3D11Buffer>(tokens_ppConstantBuffers[i], SD_COM_IF_ID3D11Buffer);
    auto ppConstantBuffers = tokens_ppConstantBuffers ? native_ppConstantBuffers.data() : nullptr;
    object->CSSetConstantBuffers(StartSlot, NumBuffers, ppConstantBuffers);
    p.ret = 0;
    return;
}
case 72: { // ID3D11DeviceContext::VSGetConstantBuffers
    auto StartSlot = (UINT)p.args[0];
    auto NumBuffers = (UINT)p.args[1];
    const uint32_t count_ppConstantBuffers = c.array_count(NumBuffers);
    auto guest_ppConstantBuffers = c.write<uint32_t>(p.args[2], count_ppConstantBuffers);
    if (guest_ppConstantBuffers) std::fill_n(guest_ppConstantBuffers, count_ppConstantBuffers, 0u);
    std::vector<ID3D11Buffer*> native_ppConstantBuffers(count_ppConstantBuffers, nullptr);
    auto ppConstantBuffers = guest_ppConstantBuffers ? native_ppConstantBuffers.data() : nullptr;
    object->VSGetConstantBuffers(StartSlot, NumBuffers, ppConstantBuffers);
    if (guest_ppConstantBuffers) for (uint32_t i=0; i<count_ppConstantBuffers; ++i) guest_ppConstantBuffers[i] = c.adopt(native_ppConstantBuffers[i], SD_COM_IF_ID3D11Buffer);
    p.ret = 0;
    return;
}
case 73: { // ID3D11DeviceContext::PSGetShaderResources
    auto StartSlot = (UINT)p.args[0];
    auto NumViews = (UINT)p.args[1];
    const uint32_t count_ppShaderResourceViews = c.array_count(NumViews);
    auto guest_ppShaderResourceViews = c.write<uint32_t>(p.args[2], count_ppShaderResourceViews);
    if (guest_ppShaderResourceViews) std::fill_n(guest_ppShaderResourceViews, count_ppShaderResourceViews, 0u);
    std::vector<ID3D11ShaderResourceView*> native_ppShaderResourceViews(count_ppShaderResourceViews, nullptr);
    auto ppShaderResourceViews = guest_ppShaderResourceViews ? native_ppShaderResourceViews.data() : nullptr;
    object->PSGetShaderResources(StartSlot, NumViews, ppShaderResourceViews);
    if (guest_ppShaderResourceViews) for (uint32_t i=0; i<count_ppShaderResourceViews; ++i) guest_ppShaderResourceViews[i] = c.adopt(native_ppShaderResourceViews[i], SD_COM_IF_ID3D11ShaderResourceView);
    p.ret = 0;
    return;
}
case 74: { // ID3D11DeviceContext::PSGetShader
    auto pNumClassInstances = c.write<UINT>(p.args[2], c.array_count(1));
    const uint32_t count_ppPixelShader = c.array_count(1);
    auto guest_ppPixelShader = c.write<uint32_t>(p.args[0], count_ppPixelShader);
    if (guest_ppPixelShader) std::fill_n(guest_ppPixelShader, count_ppPixelShader, 0u);
    std::vector<ID3D11PixelShader*> native_ppPixelShader(count_ppPixelShader, nullptr);
    auto ppPixelShader = guest_ppPixelShader ? native_ppPixelShader.data() : nullptr;
    const uint32_t count_ppClassInstances = c.array_count((pNumClassInstances ? *pNumClassInstances : 0));
    auto guest_ppClassInstances = c.write<uint32_t>(p.args[1], count_ppClassInstances);
    if (guest_ppClassInstances) std::fill_n(guest_ppClassInstances, count_ppClassInstances, 0u);
    std::vector<ID3D11ClassInstance*> native_ppClassInstances(count_ppClassInstances, nullptr);
    auto ppClassInstances = guest_ppClassInstances ? native_ppClassInstances.data() : nullptr;
    object->PSGetShader(ppPixelShader, ppClassInstances, pNumClassInstances);
    if (guest_ppPixelShader) for (uint32_t i=0; i<count_ppPixelShader; ++i) guest_ppPixelShader[i] = c.adopt(native_ppPixelShader[i], SD_COM_IF_ID3D11PixelShader);
    if (guest_ppClassInstances) for (uint32_t i=0; i<count_ppClassInstances; ++i) guest_ppClassInstances[i] = c.adopt(native_ppClassInstances[i], SD_COM_IF_ID3D11ClassInstance);
    p.ret = 0;
    return;
}
case 75: { // ID3D11DeviceContext::PSGetSamplers
    auto StartSlot = (UINT)p.args[0];
    auto NumSamplers = (UINT)p.args[1];
    const uint32_t count_ppSamplers = c.array_count(NumSamplers);
    auto guest_ppSamplers = c.write<uint32_t>(p.args[2], count_ppSamplers);
    if (guest_ppSamplers) std::fill_n(guest_ppSamplers, count_ppSamplers, 0u);
    std::vector<ID3D11SamplerState*> native_ppSamplers(count_ppSamplers, nullptr);
    auto ppSamplers = guest_ppSamplers ? native_ppSamplers.data() : nullptr;
    object->PSGetSamplers(StartSlot, NumSamplers, ppSamplers);
    if (guest_ppSamplers) for (uint32_t i=0; i<count_ppSamplers; ++i) guest_ppSamplers[i] = c.adopt(native_ppSamplers[i], SD_COM_IF_ID3D11SamplerState);
    p.ret = 0;
    return;
}
case 76: { // ID3D11DeviceContext::VSGetShader
    auto pNumClassInstances = c.write<UINT>(p.args[2], c.array_count(1));
    const uint32_t count_ppVertexShader = c.array_count(1);
    auto guest_ppVertexShader = c.write<uint32_t>(p.args[0], count_ppVertexShader);
    if (guest_ppVertexShader) std::fill_n(guest_ppVertexShader, count_ppVertexShader, 0u);
    std::vector<ID3D11VertexShader*> native_ppVertexShader(count_ppVertexShader, nullptr);
    auto ppVertexShader = guest_ppVertexShader ? native_ppVertexShader.data() : nullptr;
    const uint32_t count_ppClassInstances = c.array_count((pNumClassInstances ? *pNumClassInstances : 0));
    auto guest_ppClassInstances = c.write<uint32_t>(p.args[1], count_ppClassInstances);
    if (guest_ppClassInstances) std::fill_n(guest_ppClassInstances, count_ppClassInstances, 0u);
    std::vector<ID3D11ClassInstance*> native_ppClassInstances(count_ppClassInstances, nullptr);
    auto ppClassInstances = guest_ppClassInstances ? native_ppClassInstances.data() : nullptr;
    object->VSGetShader(ppVertexShader, ppClassInstances, pNumClassInstances);
    if (guest_ppVertexShader) for (uint32_t i=0; i<count_ppVertexShader; ++i) guest_ppVertexShader[i] = c.adopt(native_ppVertexShader[i], SD_COM_IF_ID3D11VertexShader);
    if (guest_ppClassInstances) for (uint32_t i=0; i<count_ppClassInstances; ++i) guest_ppClassInstances[i] = c.adopt(native_ppClassInstances[i], SD_COM_IF_ID3D11ClassInstance);
    p.ret = 0;
    return;
}
case 77: { // ID3D11DeviceContext::PSGetConstantBuffers
    auto StartSlot = (UINT)p.args[0];
    auto NumBuffers = (UINT)p.args[1];
    const uint32_t count_ppConstantBuffers = c.array_count(NumBuffers);
    auto guest_ppConstantBuffers = c.write<uint32_t>(p.args[2], count_ppConstantBuffers);
    if (guest_ppConstantBuffers) std::fill_n(guest_ppConstantBuffers, count_ppConstantBuffers, 0u);
    std::vector<ID3D11Buffer*> native_ppConstantBuffers(count_ppConstantBuffers, nullptr);
    auto ppConstantBuffers = guest_ppConstantBuffers ? native_ppConstantBuffers.data() : nullptr;
    object->PSGetConstantBuffers(StartSlot, NumBuffers, ppConstantBuffers);
    if (guest_ppConstantBuffers) for (uint32_t i=0; i<count_ppConstantBuffers; ++i) guest_ppConstantBuffers[i] = c.adopt(native_ppConstantBuffers[i], SD_COM_IF_ID3D11Buffer);
    p.ret = 0;
    return;
}
case 78: { // ID3D11DeviceContext::IAGetInputLayout
    const uint32_t count_ppInputLayout = c.array_count(1);
    auto guest_ppInputLayout = c.write<uint32_t>(p.args[0], count_ppInputLayout);
    if (guest_ppInputLayout) std::fill_n(guest_ppInputLayout, count_ppInputLayout, 0u);
    std::vector<ID3D11InputLayout*> native_ppInputLayout(count_ppInputLayout, nullptr);
    auto ppInputLayout = guest_ppInputLayout ? native_ppInputLayout.data() : nullptr;
    object->IAGetInputLayout(ppInputLayout);
    if (guest_ppInputLayout) for (uint32_t i=0; i<count_ppInputLayout; ++i) guest_ppInputLayout[i] = c.adopt(native_ppInputLayout[i], SD_COM_IF_ID3D11InputLayout);
    p.ret = 0;
    return;
}
case 79: { // ID3D11DeviceContext::IAGetVertexBuffers
    auto StartSlot = (UINT)p.args[0];
    auto NumBuffers = (UINT)p.args[1];
    auto pStrides = c.write<UINT>(p.args[3], c.array_count(NumBuffers));
    auto pOffsets = c.write<UINT>(p.args[4], c.array_count(NumBuffers));
    const uint32_t count_ppVertexBuffers = c.array_count(NumBuffers);
    auto guest_ppVertexBuffers = c.write<uint32_t>(p.args[2], count_ppVertexBuffers);
    if (guest_ppVertexBuffers) std::fill_n(guest_ppVertexBuffers, count_ppVertexBuffers, 0u);
    std::vector<ID3D11Buffer*> native_ppVertexBuffers(count_ppVertexBuffers, nullptr);
    auto ppVertexBuffers = guest_ppVertexBuffers ? native_ppVertexBuffers.data() : nullptr;
    object->IAGetVertexBuffers(StartSlot, NumBuffers, ppVertexBuffers, pStrides, pOffsets);
    if (guest_ppVertexBuffers) for (uint32_t i=0; i<count_ppVertexBuffers; ++i) guest_ppVertexBuffers[i] = c.adopt(native_ppVertexBuffers[i], SD_COM_IF_ID3D11Buffer);
    p.ret = 0;
    return;
}
case 80: { // ID3D11DeviceContext::IAGetIndexBuffer
    auto Offset = c.write<UINT>(p.args[2], c.array_count(1));
    const uint32_t count_pIndexBuffer = c.array_count(1);
    auto guest_pIndexBuffer = c.write<uint32_t>(p.args[0], count_pIndexBuffer);
    if (guest_pIndexBuffer) std::fill_n(guest_pIndexBuffer, count_pIndexBuffer, 0u);
    std::vector<ID3D11Buffer*> native_pIndexBuffer(count_pIndexBuffer, nullptr);
    auto pIndexBuffer = guest_pIndexBuffer ? native_pIndexBuffer.data() : nullptr;
    auto Format = c.write<DXGI_FORMAT>(p.args[1], c.array_count(1));
    object->IAGetIndexBuffer(pIndexBuffer, Format, Offset);
    if (guest_pIndexBuffer) for (uint32_t i=0; i<count_pIndexBuffer; ++i) guest_pIndexBuffer[i] = c.adopt(native_pIndexBuffer[i], SD_COM_IF_ID3D11Buffer);
    p.ret = 0;
    return;
}
case 81: { // ID3D11DeviceContext::GSGetConstantBuffers
    auto StartSlot = (UINT)p.args[0];
    auto NumBuffers = (UINT)p.args[1];
    const uint32_t count_ppConstantBuffers = c.array_count(NumBuffers);
    auto guest_ppConstantBuffers = c.write<uint32_t>(p.args[2], count_ppConstantBuffers);
    if (guest_ppConstantBuffers) std::fill_n(guest_ppConstantBuffers, count_ppConstantBuffers, 0u);
    std::vector<ID3D11Buffer*> native_ppConstantBuffers(count_ppConstantBuffers, nullptr);
    auto ppConstantBuffers = guest_ppConstantBuffers ? native_ppConstantBuffers.data() : nullptr;
    object->GSGetConstantBuffers(StartSlot, NumBuffers, ppConstantBuffers);
    if (guest_ppConstantBuffers) for (uint32_t i=0; i<count_ppConstantBuffers; ++i) guest_ppConstantBuffers[i] = c.adopt(native_ppConstantBuffers[i], SD_COM_IF_ID3D11Buffer);
    p.ret = 0;
    return;
}
case 82: { // ID3D11DeviceContext::GSGetShader
    auto pNumClassInstances = c.write<UINT>(p.args[2], c.array_count(1));
    const uint32_t count_ppGeometryShader = c.array_count(1);
    auto guest_ppGeometryShader = c.write<uint32_t>(p.args[0], count_ppGeometryShader);
    if (guest_ppGeometryShader) std::fill_n(guest_ppGeometryShader, count_ppGeometryShader, 0u);
    std::vector<ID3D11GeometryShader*> native_ppGeometryShader(count_ppGeometryShader, nullptr);
    auto ppGeometryShader = guest_ppGeometryShader ? native_ppGeometryShader.data() : nullptr;
    const uint32_t count_ppClassInstances = c.array_count((pNumClassInstances ? *pNumClassInstances : 0));
    auto guest_ppClassInstances = c.write<uint32_t>(p.args[1], count_ppClassInstances);
    if (guest_ppClassInstances) std::fill_n(guest_ppClassInstances, count_ppClassInstances, 0u);
    std::vector<ID3D11ClassInstance*> native_ppClassInstances(count_ppClassInstances, nullptr);
    auto ppClassInstances = guest_ppClassInstances ? native_ppClassInstances.data() : nullptr;
    object->GSGetShader(ppGeometryShader, ppClassInstances, pNumClassInstances);
    if (guest_ppGeometryShader) for (uint32_t i=0; i<count_ppGeometryShader; ++i) guest_ppGeometryShader[i] = c.adopt(native_ppGeometryShader[i], SD_COM_IF_ID3D11GeometryShader);
    if (guest_ppClassInstances) for (uint32_t i=0; i<count_ppClassInstances; ++i) guest_ppClassInstances[i] = c.adopt(native_ppClassInstances[i], SD_COM_IF_ID3D11ClassInstance);
    p.ret = 0;
    return;
}
case 83: { // ID3D11DeviceContext::IAGetPrimitiveTopology
    auto pTopology = c.write<D3D11_PRIMITIVE_TOPOLOGY>(p.args[0], c.array_count(1));
    object->IAGetPrimitiveTopology(pTopology);
    p.ret = 0;
    return;
}
case 84: { // ID3D11DeviceContext::VSGetShaderResources
    auto StartSlot = (UINT)p.args[0];
    auto NumViews = (UINT)p.args[1];
    const uint32_t count_ppShaderResourceViews = c.array_count(NumViews);
    auto guest_ppShaderResourceViews = c.write<uint32_t>(p.args[2], count_ppShaderResourceViews);
    if (guest_ppShaderResourceViews) std::fill_n(guest_ppShaderResourceViews, count_ppShaderResourceViews, 0u);
    std::vector<ID3D11ShaderResourceView*> native_ppShaderResourceViews(count_ppShaderResourceViews, nullptr);
    auto ppShaderResourceViews = guest_ppShaderResourceViews ? native_ppShaderResourceViews.data() : nullptr;
    object->VSGetShaderResources(StartSlot, NumViews, ppShaderResourceViews);
    if (guest_ppShaderResourceViews) for (uint32_t i=0; i<count_ppShaderResourceViews; ++i) guest_ppShaderResourceViews[i] = c.adopt(native_ppShaderResourceViews[i], SD_COM_IF_ID3D11ShaderResourceView);
    p.ret = 0;
    return;
}
case 85: { // ID3D11DeviceContext::VSGetSamplers
    auto StartSlot = (UINT)p.args[0];
    auto NumSamplers = (UINT)p.args[1];
    const uint32_t count_ppSamplers = c.array_count(NumSamplers);
    auto guest_ppSamplers = c.write<uint32_t>(p.args[2], count_ppSamplers);
    if (guest_ppSamplers) std::fill_n(guest_ppSamplers, count_ppSamplers, 0u);
    std::vector<ID3D11SamplerState*> native_ppSamplers(count_ppSamplers, nullptr);
    auto ppSamplers = guest_ppSamplers ? native_ppSamplers.data() : nullptr;
    object->VSGetSamplers(StartSlot, NumSamplers, ppSamplers);
    if (guest_ppSamplers) for (uint32_t i=0; i<count_ppSamplers; ++i) guest_ppSamplers[i] = c.adopt(native_ppSamplers[i], SD_COM_IF_ID3D11SamplerState);
    p.ret = 0;
    return;
}
case 86: { // ID3D11DeviceContext::GetPredication
    const uint32_t count_ppPredicate = c.array_count(1);
    auto guest_ppPredicate = c.write<uint32_t>(p.args[0], count_ppPredicate);
    if (guest_ppPredicate) std::fill_n(guest_ppPredicate, count_ppPredicate, 0u);
    std::vector<ID3D11Predicate*> native_ppPredicate(count_ppPredicate, nullptr);
    auto ppPredicate = guest_ppPredicate ? native_ppPredicate.data() : nullptr;
    auto pPredicateValue = c.write<WINBOOL>(p.args[1], c.array_count(1));
    object->GetPredication(ppPredicate, pPredicateValue);
    if (guest_ppPredicate) for (uint32_t i=0; i<count_ppPredicate; ++i) guest_ppPredicate[i] = c.adopt(native_ppPredicate[i], SD_COM_IF_ID3D11Predicate);
    p.ret = 0;
    return;
}
case 87: { // ID3D11DeviceContext::GSGetShaderResources
    auto StartSlot = (UINT)p.args[0];
    auto NumViews = (UINT)p.args[1];
    const uint32_t count_ppShaderResourceViews = c.array_count(NumViews);
    auto guest_ppShaderResourceViews = c.write<uint32_t>(p.args[2], count_ppShaderResourceViews);
    if (guest_ppShaderResourceViews) std::fill_n(guest_ppShaderResourceViews, count_ppShaderResourceViews, 0u);
    std::vector<ID3D11ShaderResourceView*> native_ppShaderResourceViews(count_ppShaderResourceViews, nullptr);
    auto ppShaderResourceViews = guest_ppShaderResourceViews ? native_ppShaderResourceViews.data() : nullptr;
    object->GSGetShaderResources(StartSlot, NumViews, ppShaderResourceViews);
    if (guest_ppShaderResourceViews) for (uint32_t i=0; i<count_ppShaderResourceViews; ++i) guest_ppShaderResourceViews[i] = c.adopt(native_ppShaderResourceViews[i], SD_COM_IF_ID3D11ShaderResourceView);
    p.ret = 0;
    return;
}
case 88: { // ID3D11DeviceContext::GSGetSamplers
    auto StartSlot = (UINT)p.args[0];
    auto NumSamplers = (UINT)p.args[1];
    const uint32_t count_ppSamplers = c.array_count(NumSamplers);
    auto guest_ppSamplers = c.write<uint32_t>(p.args[2], count_ppSamplers);
    if (guest_ppSamplers) std::fill_n(guest_ppSamplers, count_ppSamplers, 0u);
    std::vector<ID3D11SamplerState*> native_ppSamplers(count_ppSamplers, nullptr);
    auto ppSamplers = guest_ppSamplers ? native_ppSamplers.data() : nullptr;
    object->GSGetSamplers(StartSlot, NumSamplers, ppSamplers);
    if (guest_ppSamplers) for (uint32_t i=0; i<count_ppSamplers; ++i) guest_ppSamplers[i] = c.adopt(native_ppSamplers[i], SD_COM_IF_ID3D11SamplerState);
    p.ret = 0;
    return;
}
case 89: { // ID3D11DeviceContext::OMGetRenderTargets
    auto NumViews = (UINT)p.args[0];
    const uint32_t count_ppRenderTargetViews = c.array_count(NumViews);
    auto guest_ppRenderTargetViews = c.write<uint32_t>(p.args[1], count_ppRenderTargetViews);
    if (guest_ppRenderTargetViews) std::fill_n(guest_ppRenderTargetViews, count_ppRenderTargetViews, 0u);
    std::vector<ID3D11RenderTargetView*> native_ppRenderTargetViews(count_ppRenderTargetViews, nullptr);
    auto ppRenderTargetViews = guest_ppRenderTargetViews ? native_ppRenderTargetViews.data() : nullptr;
    const uint32_t count_ppDepthStencilView = c.array_count(1);
    auto guest_ppDepthStencilView = c.write<uint32_t>(p.args[2], count_ppDepthStencilView);
    if (guest_ppDepthStencilView) std::fill_n(guest_ppDepthStencilView, count_ppDepthStencilView, 0u);
    std::vector<ID3D11DepthStencilView*> native_ppDepthStencilView(count_ppDepthStencilView, nullptr);
    auto ppDepthStencilView = guest_ppDepthStencilView ? native_ppDepthStencilView.data() : nullptr;
    object->OMGetRenderTargets(NumViews, ppRenderTargetViews, ppDepthStencilView);
    if (guest_ppRenderTargetViews) for (uint32_t i=0; i<count_ppRenderTargetViews; ++i) guest_ppRenderTargetViews[i] = c.adopt(native_ppRenderTargetViews[i], SD_COM_IF_ID3D11RenderTargetView);
    if (guest_ppDepthStencilView) for (uint32_t i=0; i<count_ppDepthStencilView; ++i) guest_ppDepthStencilView[i] = c.adopt(native_ppDepthStencilView[i], SD_COM_IF_ID3D11DepthStencilView);
    p.ret = 0;
    return;
}
case 90: { // ID3D11DeviceContext::OMGetRenderTargetsAndUnorderedAccessViews
    auto NumRTVs = (UINT)p.args[0];
    auto UAVStartSlot = (UINT)p.args[3];
    auto NumUAVs = (UINT)p.args[4];
    const uint32_t count_ppRenderTargetViews = c.array_count(NumRTVs);
    auto guest_ppRenderTargetViews = c.write<uint32_t>(p.args[1], count_ppRenderTargetViews);
    if (guest_ppRenderTargetViews) std::fill_n(guest_ppRenderTargetViews, count_ppRenderTargetViews, 0u);
    std::vector<ID3D11RenderTargetView*> native_ppRenderTargetViews(count_ppRenderTargetViews, nullptr);
    auto ppRenderTargetViews = guest_ppRenderTargetViews ? native_ppRenderTargetViews.data() : nullptr;
    const uint32_t count_ppDepthStencilView = c.array_count(1);
    auto guest_ppDepthStencilView = c.write<uint32_t>(p.args[2], count_ppDepthStencilView);
    if (guest_ppDepthStencilView) std::fill_n(guest_ppDepthStencilView, count_ppDepthStencilView, 0u);
    std::vector<ID3D11DepthStencilView*> native_ppDepthStencilView(count_ppDepthStencilView, nullptr);
    auto ppDepthStencilView = guest_ppDepthStencilView ? native_ppDepthStencilView.data() : nullptr;
    const uint32_t count_ppUnorderedAccessViews = c.array_count(NumUAVs);
    auto guest_ppUnorderedAccessViews = c.write<uint32_t>(p.args[5], count_ppUnorderedAccessViews);
    if (guest_ppUnorderedAccessViews) std::fill_n(guest_ppUnorderedAccessViews, count_ppUnorderedAccessViews, 0u);
    std::vector<ID3D11UnorderedAccessView*> native_ppUnorderedAccessViews(count_ppUnorderedAccessViews, nullptr);
    auto ppUnorderedAccessViews = guest_ppUnorderedAccessViews ? native_ppUnorderedAccessViews.data() : nullptr;
    object->OMGetRenderTargetsAndUnorderedAccessViews(NumRTVs, ppRenderTargetViews, ppDepthStencilView, UAVStartSlot, NumUAVs, ppUnorderedAccessViews);
    if (guest_ppRenderTargetViews) for (uint32_t i=0; i<count_ppRenderTargetViews; ++i) guest_ppRenderTargetViews[i] = c.adopt(native_ppRenderTargetViews[i], SD_COM_IF_ID3D11RenderTargetView);
    if (guest_ppDepthStencilView) for (uint32_t i=0; i<count_ppDepthStencilView; ++i) guest_ppDepthStencilView[i] = c.adopt(native_ppDepthStencilView[i], SD_COM_IF_ID3D11DepthStencilView);
    if (guest_ppUnorderedAccessViews) for (uint32_t i=0; i<count_ppUnorderedAccessViews; ++i) guest_ppUnorderedAccessViews[i] = c.adopt(native_ppUnorderedAccessViews[i], SD_COM_IF_ID3D11UnorderedAccessView);
    p.ret = 0;
    return;
}
case 91: { // ID3D11DeviceContext::OMGetBlendState
    auto pSampleMask = c.write<UINT>(p.args[2], c.array_count(1));
    const uint32_t count_ppBlendState = c.array_count(1);
    auto guest_ppBlendState = c.write<uint32_t>(p.args[0], count_ppBlendState);
    if (guest_ppBlendState) std::fill_n(guest_ppBlendState, count_ppBlendState, 0u);
    std::vector<ID3D11BlendState*> native_ppBlendState(count_ppBlendState, nullptr);
    auto ppBlendState = guest_ppBlendState ? native_ppBlendState.data() : nullptr;
    auto BlendFactor = c.write<FLOAT>(p.args[1], c.array_count(4));
    object->OMGetBlendState(ppBlendState, BlendFactor, pSampleMask);
    if (guest_ppBlendState) for (uint32_t i=0; i<count_ppBlendState; ++i) guest_ppBlendState[i] = c.adopt(native_ppBlendState[i], SD_COM_IF_ID3D11BlendState);
    p.ret = 0;
    return;
}
case 92: { // ID3D11DeviceContext::OMGetDepthStencilState
    auto pStencilRef = c.write<UINT>(p.args[1], c.array_count(1));
    const uint32_t count_ppDepthStencilState = c.array_count(1);
    auto guest_ppDepthStencilState = c.write<uint32_t>(p.args[0], count_ppDepthStencilState);
    if (guest_ppDepthStencilState) std::fill_n(guest_ppDepthStencilState, count_ppDepthStencilState, 0u);
    std::vector<ID3D11DepthStencilState*> native_ppDepthStencilState(count_ppDepthStencilState, nullptr);
    auto ppDepthStencilState = guest_ppDepthStencilState ? native_ppDepthStencilState.data() : nullptr;
    object->OMGetDepthStencilState(ppDepthStencilState, pStencilRef);
    if (guest_ppDepthStencilState) for (uint32_t i=0; i<count_ppDepthStencilState; ++i) guest_ppDepthStencilState[i] = c.adopt(native_ppDepthStencilState[i], SD_COM_IF_ID3D11DepthStencilState);
    p.ret = 0;
    return;
}
case 93: { // ID3D11DeviceContext::SOGetTargets
    auto NumBuffers = (UINT)p.args[0];
    const uint32_t count_ppSOTargets = c.array_count(NumBuffers);
    auto guest_ppSOTargets = c.write<uint32_t>(p.args[1], count_ppSOTargets);
    if (guest_ppSOTargets) std::fill_n(guest_ppSOTargets, count_ppSOTargets, 0u);
    std::vector<ID3D11Buffer*> native_ppSOTargets(count_ppSOTargets, nullptr);
    auto ppSOTargets = guest_ppSOTargets ? native_ppSOTargets.data() : nullptr;
    object->SOGetTargets(NumBuffers, ppSOTargets);
    if (guest_ppSOTargets) for (uint32_t i=0; i<count_ppSOTargets; ++i) guest_ppSOTargets[i] = c.adopt(native_ppSOTargets[i], SD_COM_IF_ID3D11Buffer);
    p.ret = 0;
    return;
}
case 94: { // ID3D11DeviceContext::RSGetState
    const uint32_t count_ppRasterizerState = c.array_count(1);
    auto guest_ppRasterizerState = c.write<uint32_t>(p.args[0], count_ppRasterizerState);
    if (guest_ppRasterizerState) std::fill_n(guest_ppRasterizerState, count_ppRasterizerState, 0u);
    std::vector<ID3D11RasterizerState*> native_ppRasterizerState(count_ppRasterizerState, nullptr);
    auto ppRasterizerState = guest_ppRasterizerState ? native_ppRasterizerState.data() : nullptr;
    object->RSGetState(ppRasterizerState);
    if (guest_ppRasterizerState) for (uint32_t i=0; i<count_ppRasterizerState; ++i) guest_ppRasterizerState[i] = c.adopt(native_ppRasterizerState[i], SD_COM_IF_ID3D11RasterizerState);
    p.ret = 0;
    return;
}
case 95: { // ID3D11DeviceContext::RSGetViewports
    auto pNumViewports = c.write<UINT>(p.args[0], c.array_count(1));
    auto pViewports = c.write<D3D11_VIEWPORT>(p.args[1], c.array_count((pNumViewports ? *pNumViewports : 0)));
    object->RSGetViewports(pNumViewports, pViewports);
    p.ret = 0;
    return;
}
case 96: { // ID3D11DeviceContext::RSGetScissorRects
    auto pNumRects = c.write<UINT>(p.args[0], c.array_count(1));
    auto pRects = c.write<D3D11_RECT>(p.args[1], c.array_count((pNumRects ? *pNumRects : 0)));
    object->RSGetScissorRects(pNumRects, pRects);
    p.ret = 0;
    return;
}
case 97: { // ID3D11DeviceContext::HSGetShaderResources
    auto StartSlot = (UINT)p.args[0];
    auto NumViews = (UINT)p.args[1];
    const uint32_t count_ppShaderResourceViews = c.array_count(NumViews);
    auto guest_ppShaderResourceViews = c.write<uint32_t>(p.args[2], count_ppShaderResourceViews);
    if (guest_ppShaderResourceViews) std::fill_n(guest_ppShaderResourceViews, count_ppShaderResourceViews, 0u);
    std::vector<ID3D11ShaderResourceView*> native_ppShaderResourceViews(count_ppShaderResourceViews, nullptr);
    auto ppShaderResourceViews = guest_ppShaderResourceViews ? native_ppShaderResourceViews.data() : nullptr;
    object->HSGetShaderResources(StartSlot, NumViews, ppShaderResourceViews);
    if (guest_ppShaderResourceViews) for (uint32_t i=0; i<count_ppShaderResourceViews; ++i) guest_ppShaderResourceViews[i] = c.adopt(native_ppShaderResourceViews[i], SD_COM_IF_ID3D11ShaderResourceView);
    p.ret = 0;
    return;
}
case 98: { // ID3D11DeviceContext::HSGetShader
    auto pNumClassInstances = c.write<UINT>(p.args[2], c.array_count(1));
    const uint32_t count_ppHullShader = c.array_count(1);
    auto guest_ppHullShader = c.write<uint32_t>(p.args[0], count_ppHullShader);
    if (guest_ppHullShader) std::fill_n(guest_ppHullShader, count_ppHullShader, 0u);
    std::vector<ID3D11HullShader*> native_ppHullShader(count_ppHullShader, nullptr);
    auto ppHullShader = guest_ppHullShader ? native_ppHullShader.data() : nullptr;
    const uint32_t count_ppClassInstances = c.array_count((pNumClassInstances ? *pNumClassInstances : 0));
    auto guest_ppClassInstances = c.write<uint32_t>(p.args[1], count_ppClassInstances);
    if (guest_ppClassInstances) std::fill_n(guest_ppClassInstances, count_ppClassInstances, 0u);
    std::vector<ID3D11ClassInstance*> native_ppClassInstances(count_ppClassInstances, nullptr);
    auto ppClassInstances = guest_ppClassInstances ? native_ppClassInstances.data() : nullptr;
    object->HSGetShader(ppHullShader, ppClassInstances, pNumClassInstances);
    if (guest_ppHullShader) for (uint32_t i=0; i<count_ppHullShader; ++i) guest_ppHullShader[i] = c.adopt(native_ppHullShader[i], SD_COM_IF_ID3D11HullShader);
    if (guest_ppClassInstances) for (uint32_t i=0; i<count_ppClassInstances; ++i) guest_ppClassInstances[i] = c.adopt(native_ppClassInstances[i], SD_COM_IF_ID3D11ClassInstance);
    p.ret = 0;
    return;
}
case 99: { // ID3D11DeviceContext::HSGetSamplers
    auto StartSlot = (UINT)p.args[0];
    auto NumSamplers = (UINT)p.args[1];
    const uint32_t count_ppSamplers = c.array_count(NumSamplers);
    auto guest_ppSamplers = c.write<uint32_t>(p.args[2], count_ppSamplers);
    if (guest_ppSamplers) std::fill_n(guest_ppSamplers, count_ppSamplers, 0u);
    std::vector<ID3D11SamplerState*> native_ppSamplers(count_ppSamplers, nullptr);
    auto ppSamplers = guest_ppSamplers ? native_ppSamplers.data() : nullptr;
    object->HSGetSamplers(StartSlot, NumSamplers, ppSamplers);
    if (guest_ppSamplers) for (uint32_t i=0; i<count_ppSamplers; ++i) guest_ppSamplers[i] = c.adopt(native_ppSamplers[i], SD_COM_IF_ID3D11SamplerState);
    p.ret = 0;
    return;
}
case 100: { // ID3D11DeviceContext::HSGetConstantBuffers
    auto StartSlot = (UINT)p.args[0];
    auto NumBuffers = (UINT)p.args[1];
    const uint32_t count_ppConstantBuffers = c.array_count(NumBuffers);
    auto guest_ppConstantBuffers = c.write<uint32_t>(p.args[2], count_ppConstantBuffers);
    if (guest_ppConstantBuffers) std::fill_n(guest_ppConstantBuffers, count_ppConstantBuffers, 0u);
    std::vector<ID3D11Buffer*> native_ppConstantBuffers(count_ppConstantBuffers, nullptr);
    auto ppConstantBuffers = guest_ppConstantBuffers ? native_ppConstantBuffers.data() : nullptr;
    object->HSGetConstantBuffers(StartSlot, NumBuffers, ppConstantBuffers);
    if (guest_ppConstantBuffers) for (uint32_t i=0; i<count_ppConstantBuffers; ++i) guest_ppConstantBuffers[i] = c.adopt(native_ppConstantBuffers[i], SD_COM_IF_ID3D11Buffer);
    p.ret = 0;
    return;
}
case 101: { // ID3D11DeviceContext::DSGetShaderResources
    auto StartSlot = (UINT)p.args[0];
    auto NumViews = (UINT)p.args[1];
    const uint32_t count_ppShaderResourceViews = c.array_count(NumViews);
    auto guest_ppShaderResourceViews = c.write<uint32_t>(p.args[2], count_ppShaderResourceViews);
    if (guest_ppShaderResourceViews) std::fill_n(guest_ppShaderResourceViews, count_ppShaderResourceViews, 0u);
    std::vector<ID3D11ShaderResourceView*> native_ppShaderResourceViews(count_ppShaderResourceViews, nullptr);
    auto ppShaderResourceViews = guest_ppShaderResourceViews ? native_ppShaderResourceViews.data() : nullptr;
    object->DSGetShaderResources(StartSlot, NumViews, ppShaderResourceViews);
    if (guest_ppShaderResourceViews) for (uint32_t i=0; i<count_ppShaderResourceViews; ++i) guest_ppShaderResourceViews[i] = c.adopt(native_ppShaderResourceViews[i], SD_COM_IF_ID3D11ShaderResourceView);
    p.ret = 0;
    return;
}
case 102: { // ID3D11DeviceContext::DSGetShader
    auto pNumClassInstances = c.write<UINT>(p.args[2], c.array_count(1));
    const uint32_t count_ppDomainShader = c.array_count(1);
    auto guest_ppDomainShader = c.write<uint32_t>(p.args[0], count_ppDomainShader);
    if (guest_ppDomainShader) std::fill_n(guest_ppDomainShader, count_ppDomainShader, 0u);
    std::vector<ID3D11DomainShader*> native_ppDomainShader(count_ppDomainShader, nullptr);
    auto ppDomainShader = guest_ppDomainShader ? native_ppDomainShader.data() : nullptr;
    const uint32_t count_ppClassInstances = c.array_count((pNumClassInstances ? *pNumClassInstances : 0));
    auto guest_ppClassInstances = c.write<uint32_t>(p.args[1], count_ppClassInstances);
    if (guest_ppClassInstances) std::fill_n(guest_ppClassInstances, count_ppClassInstances, 0u);
    std::vector<ID3D11ClassInstance*> native_ppClassInstances(count_ppClassInstances, nullptr);
    auto ppClassInstances = guest_ppClassInstances ? native_ppClassInstances.data() : nullptr;
    object->DSGetShader(ppDomainShader, ppClassInstances, pNumClassInstances);
    if (guest_ppDomainShader) for (uint32_t i=0; i<count_ppDomainShader; ++i) guest_ppDomainShader[i] = c.adopt(native_ppDomainShader[i], SD_COM_IF_ID3D11DomainShader);
    if (guest_ppClassInstances) for (uint32_t i=0; i<count_ppClassInstances; ++i) guest_ppClassInstances[i] = c.adopt(native_ppClassInstances[i], SD_COM_IF_ID3D11ClassInstance);
    p.ret = 0;
    return;
}
case 103: { // ID3D11DeviceContext::DSGetSamplers
    auto StartSlot = (UINT)p.args[0];
    auto NumSamplers = (UINT)p.args[1];
    const uint32_t count_ppSamplers = c.array_count(NumSamplers);
    auto guest_ppSamplers = c.write<uint32_t>(p.args[2], count_ppSamplers);
    if (guest_ppSamplers) std::fill_n(guest_ppSamplers, count_ppSamplers, 0u);
    std::vector<ID3D11SamplerState*> native_ppSamplers(count_ppSamplers, nullptr);
    auto ppSamplers = guest_ppSamplers ? native_ppSamplers.data() : nullptr;
    object->DSGetSamplers(StartSlot, NumSamplers, ppSamplers);
    if (guest_ppSamplers) for (uint32_t i=0; i<count_ppSamplers; ++i) guest_ppSamplers[i] = c.adopt(native_ppSamplers[i], SD_COM_IF_ID3D11SamplerState);
    p.ret = 0;
    return;
}
case 104: { // ID3D11DeviceContext::DSGetConstantBuffers
    auto StartSlot = (UINT)p.args[0];
    auto NumBuffers = (UINT)p.args[1];
    const uint32_t count_ppConstantBuffers = c.array_count(NumBuffers);
    auto guest_ppConstantBuffers = c.write<uint32_t>(p.args[2], count_ppConstantBuffers);
    if (guest_ppConstantBuffers) std::fill_n(guest_ppConstantBuffers, count_ppConstantBuffers, 0u);
    std::vector<ID3D11Buffer*> native_ppConstantBuffers(count_ppConstantBuffers, nullptr);
    auto ppConstantBuffers = guest_ppConstantBuffers ? native_ppConstantBuffers.data() : nullptr;
    object->DSGetConstantBuffers(StartSlot, NumBuffers, ppConstantBuffers);
    if (guest_ppConstantBuffers) for (uint32_t i=0; i<count_ppConstantBuffers; ++i) guest_ppConstantBuffers[i] = c.adopt(native_ppConstantBuffers[i], SD_COM_IF_ID3D11Buffer);
    p.ret = 0;
    return;
}
case 105: { // ID3D11DeviceContext::CSGetShaderResources
    auto StartSlot = (UINT)p.args[0];
    auto NumViews = (UINT)p.args[1];
    const uint32_t count_ppShaderResourceViews = c.array_count(NumViews);
    auto guest_ppShaderResourceViews = c.write<uint32_t>(p.args[2], count_ppShaderResourceViews);
    if (guest_ppShaderResourceViews) std::fill_n(guest_ppShaderResourceViews, count_ppShaderResourceViews, 0u);
    std::vector<ID3D11ShaderResourceView*> native_ppShaderResourceViews(count_ppShaderResourceViews, nullptr);
    auto ppShaderResourceViews = guest_ppShaderResourceViews ? native_ppShaderResourceViews.data() : nullptr;
    object->CSGetShaderResources(StartSlot, NumViews, ppShaderResourceViews);
    if (guest_ppShaderResourceViews) for (uint32_t i=0; i<count_ppShaderResourceViews; ++i) guest_ppShaderResourceViews[i] = c.adopt(native_ppShaderResourceViews[i], SD_COM_IF_ID3D11ShaderResourceView);
    p.ret = 0;
    return;
}
case 106: { // ID3D11DeviceContext::CSGetUnorderedAccessViews
    auto StartSlot = (UINT)p.args[0];
    auto NumUAVs = (UINT)p.args[1];
    const uint32_t count_ppUnorderedAccessViews = c.array_count(NumUAVs);
    auto guest_ppUnorderedAccessViews = c.write<uint32_t>(p.args[2], count_ppUnorderedAccessViews);
    if (guest_ppUnorderedAccessViews) std::fill_n(guest_ppUnorderedAccessViews, count_ppUnorderedAccessViews, 0u);
    std::vector<ID3D11UnorderedAccessView*> native_ppUnorderedAccessViews(count_ppUnorderedAccessViews, nullptr);
    auto ppUnorderedAccessViews = guest_ppUnorderedAccessViews ? native_ppUnorderedAccessViews.data() : nullptr;
    object->CSGetUnorderedAccessViews(StartSlot, NumUAVs, ppUnorderedAccessViews);
    if (guest_ppUnorderedAccessViews) for (uint32_t i=0; i<count_ppUnorderedAccessViews; ++i) guest_ppUnorderedAccessViews[i] = c.adopt(native_ppUnorderedAccessViews[i], SD_COM_IF_ID3D11UnorderedAccessView);
    p.ret = 0;
    return;
}
case 107: { // ID3D11DeviceContext::CSGetShader
    auto pNumClassInstances = c.write<UINT>(p.args[2], c.array_count(1));
    const uint32_t count_ppComputeShader = c.array_count(1);
    auto guest_ppComputeShader = c.write<uint32_t>(p.args[0], count_ppComputeShader);
    if (guest_ppComputeShader) std::fill_n(guest_ppComputeShader, count_ppComputeShader, 0u);
    std::vector<ID3D11ComputeShader*> native_ppComputeShader(count_ppComputeShader, nullptr);
    auto ppComputeShader = guest_ppComputeShader ? native_ppComputeShader.data() : nullptr;
    const uint32_t count_ppClassInstances = c.array_count((pNumClassInstances ? *pNumClassInstances : 0));
    auto guest_ppClassInstances = c.write<uint32_t>(p.args[1], count_ppClassInstances);
    if (guest_ppClassInstances) std::fill_n(guest_ppClassInstances, count_ppClassInstances, 0u);
    std::vector<ID3D11ClassInstance*> native_ppClassInstances(count_ppClassInstances, nullptr);
    auto ppClassInstances = guest_ppClassInstances ? native_ppClassInstances.data() : nullptr;
    object->CSGetShader(ppComputeShader, ppClassInstances, pNumClassInstances);
    if (guest_ppComputeShader) for (uint32_t i=0; i<count_ppComputeShader; ++i) guest_ppComputeShader[i] = c.adopt(native_ppComputeShader[i], SD_COM_IF_ID3D11ComputeShader);
    if (guest_ppClassInstances) for (uint32_t i=0; i<count_ppClassInstances; ++i) guest_ppClassInstances[i] = c.adopt(native_ppClassInstances[i], SD_COM_IF_ID3D11ClassInstance);
    p.ret = 0;
    return;
}
case 108: { // ID3D11DeviceContext::CSGetSamplers
    auto StartSlot = (UINT)p.args[0];
    auto NumSamplers = (UINT)p.args[1];
    const uint32_t count_ppSamplers = c.array_count(NumSamplers);
    auto guest_ppSamplers = c.write<uint32_t>(p.args[2], count_ppSamplers);
    if (guest_ppSamplers) std::fill_n(guest_ppSamplers, count_ppSamplers, 0u);
    std::vector<ID3D11SamplerState*> native_ppSamplers(count_ppSamplers, nullptr);
    auto ppSamplers = guest_ppSamplers ? native_ppSamplers.data() : nullptr;
    object->CSGetSamplers(StartSlot, NumSamplers, ppSamplers);
    if (guest_ppSamplers) for (uint32_t i=0; i<count_ppSamplers; ++i) guest_ppSamplers[i] = c.adopt(native_ppSamplers[i], SD_COM_IF_ID3D11SamplerState);
    p.ret = 0;
    return;
}
case 109: { // ID3D11DeviceContext::CSGetConstantBuffers
    auto StartSlot = (UINT)p.args[0];
    auto NumBuffers = (UINT)p.args[1];
    const uint32_t count_ppConstantBuffers = c.array_count(NumBuffers);
    auto guest_ppConstantBuffers = c.write<uint32_t>(p.args[2], count_ppConstantBuffers);
    if (guest_ppConstantBuffers) std::fill_n(guest_ppConstantBuffers, count_ppConstantBuffers, 0u);
    std::vector<ID3D11Buffer*> native_ppConstantBuffers(count_ppConstantBuffers, nullptr);
    auto ppConstantBuffers = guest_ppConstantBuffers ? native_ppConstantBuffers.data() : nullptr;
    object->CSGetConstantBuffers(StartSlot, NumBuffers, ppConstantBuffers);
    if (guest_ppConstantBuffers) for (uint32_t i=0; i<count_ppConstantBuffers; ++i) guest_ppConstantBuffers[i] = c.adopt(native_ppConstantBuffers[i], SD_COM_IF_ID3D11Buffer);
    p.ret = 0;
    return;
}
case 110: { // ID3D11DeviceContext::ClearState
    object->ClearState();
    p.ret = 0;
    return;
}
case 111: { // ID3D11DeviceContext::Flush
    object->Flush();
    p.ret = 0;
    return;
}
case 112: { // ID3D11DeviceContext::GetType
    auto result = object->GetType();
    p.ret = result;
    return;
}
case 113: { // ID3D11DeviceContext::GetContextFlags
    auto result = object->GetContextFlags();
    p.ret = result;
    return;
}
case 114: { // ID3D11DeviceContext::FinishCommandList
    auto RestoreDeferredContextState = (WINBOOL)p.args[0];
    const uint32_t count_ppCommandList = c.array_count(1);
    auto guest_ppCommandList = c.write<uint32_t>(p.args[1], count_ppCommandList);
    if (guest_ppCommandList) std::fill_n(guest_ppCommandList, count_ppCommandList, 0u);
    std::vector<ID3D11CommandList*> native_ppCommandList(count_ppCommandList, nullptr);
    auto ppCommandList = guest_ppCommandList ? native_ppCommandList.data() : nullptr;
    auto result = object->FinishCommandList(RestoreDeferredContextState, ppCommandList);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_ppCommandList) for (uint32_t i=0; i<count_ppCommandList; ++i) guest_ppCommandList[i] = c.adopt(native_ppCommandList[i], SD_COM_IF_ID3D11CommandList);
    p.ret = result;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11DomainShader: {
    auto object = c.object<ID3D11DomainShader>(p.object, SD_COM_IF_ID3D11DomainShader);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11DomainShader::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11DomainShader::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11DomainShader::Release
    return c.Release(p);
}
case 3: { // ID3D11DomainShader::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11DomainShader::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11DomainShader::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11DomainShader::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11GeometryShader: {
    auto object = c.object<ID3D11GeometryShader>(p.object, SD_COM_IF_ID3D11GeometryShader);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11GeometryShader::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11GeometryShader::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11GeometryShader::Release
    return c.Release(p);
}
case 3: { // ID3D11GeometryShader::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11GeometryShader::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11GeometryShader::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11GeometryShader::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11HullShader: {
    auto object = c.object<ID3D11HullShader>(p.object, SD_COM_IF_ID3D11HullShader);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11HullShader::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11HullShader::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11HullShader::Release
    return c.Release(p);
}
case 3: { // ID3D11HullShader::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11HullShader::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11HullShader::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11HullShader::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11InputLayout: {
    auto object = c.object<ID3D11InputLayout>(p.object, SD_COM_IF_ID3D11InputLayout);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11InputLayout::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11InputLayout::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11InputLayout::Release
    return c.Release(p);
}
case 3: { // ID3D11InputLayout::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11InputLayout::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11InputLayout::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11InputLayout::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11PixelShader: {
    auto object = c.object<ID3D11PixelShader>(p.object, SD_COM_IF_ID3D11PixelShader);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11PixelShader::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11PixelShader::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11PixelShader::Release
    return c.Release(p);
}
case 3: { // ID3D11PixelShader::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11PixelShader::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11PixelShader::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11PixelShader::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11Predicate: {
    auto object = c.object<ID3D11Predicate>(p.object, SD_COM_IF_ID3D11Predicate);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11Predicate::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11Predicate::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11Predicate::Release
    return c.Release(p);
}
case 3: { // ID3D11Predicate::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11Predicate::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11Predicate::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11Predicate::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
case 7: { // ID3D11Predicate::GetDataSize
    auto result = object->GetDataSize();
    p.ret = result;
    return;
}
case 8: { // ID3D11Predicate::GetDesc
    auto pDesc = c.write<D3D11_QUERY_DESC>(p.args[0], c.array_count(1));
    object->GetDesc(pDesc);
    p.ret = 0;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11Query: {
    auto object = c.object<ID3D11Query>(p.object, SD_COM_IF_ID3D11Query);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11Query::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11Query::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11Query::Release
    return c.Release(p);
}
case 3: { // ID3D11Query::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11Query::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11Query::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11Query::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
case 7: { // ID3D11Query::GetDataSize
    auto result = object->GetDataSize();
    p.ret = result;
    return;
}
case 8: { // ID3D11Query::GetDesc
    auto pDesc = c.write<D3D11_QUERY_DESC>(p.args[0], c.array_count(1));
    object->GetDesc(pDesc);
    p.ret = 0;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11RasterizerState: {
    auto object = c.object<ID3D11RasterizerState>(p.object, SD_COM_IF_ID3D11RasterizerState);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11RasterizerState::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11RasterizerState::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11RasterizerState::Release
    return c.Release(p);
}
case 3: { // ID3D11RasterizerState::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11RasterizerState::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11RasterizerState::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11RasterizerState::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
case 7: { // ID3D11RasterizerState::GetDesc
    auto pDesc = c.write<D3D11_RASTERIZER_DESC>(p.args[0], c.array_count(1));
    object->GetDesc(pDesc);
    p.ret = 0;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11RenderTargetView: {
    auto object = c.object<ID3D11RenderTargetView>(p.object, SD_COM_IF_ID3D11RenderTargetView);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11RenderTargetView::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11RenderTargetView::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11RenderTargetView::Release
    return c.Release(p);
}
case 3: { // ID3D11RenderTargetView::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11RenderTargetView::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11RenderTargetView::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11RenderTargetView::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
case 7: { // ID3D11RenderTargetView::GetResource
    const uint32_t count_ppResource = c.array_count(1);
    auto guest_ppResource = c.write<uint32_t>(p.args[0], count_ppResource);
    if (guest_ppResource) std::fill_n(guest_ppResource, count_ppResource, 0u);
    std::vector<ID3D11Resource*> native_ppResource(count_ppResource, nullptr);
    auto ppResource = guest_ppResource ? native_ppResource.data() : nullptr;
    object->GetResource(ppResource);
    if (guest_ppResource) for (uint32_t i=0; i<count_ppResource; ++i) guest_ppResource[i] = c.adopt(native_ppResource[i], SD_COM_IF_ID3D11Resource);
    p.ret = 0;
    return;
}
case 8: { // ID3D11RenderTargetView::GetDesc
    auto pDesc = c.write<D3D11_RENDER_TARGET_VIEW_DESC>(p.args[0], c.array_count(1));
    object->GetDesc(pDesc);
    p.ret = 0;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11Resource: {
    auto object = c.object<ID3D11Resource>(p.object, SD_COM_IF_ID3D11Resource);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11Resource::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11Resource::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11Resource::Release
    return c.Release(p);
}
case 3: { // ID3D11Resource::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11Resource::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11Resource::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11Resource::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
case 7: { // ID3D11Resource::GetType
    auto pResourceDimension = c.write<D3D11_RESOURCE_DIMENSION>(p.args[0], c.array_count(1));
    object->GetType(pResourceDimension);
    p.ret = 0;
    return;
}
case 8: { // ID3D11Resource::SetEvictionPriority
    auto EvictionPriority = (UINT)p.args[0];
    object->SetEvictionPriority(EvictionPriority);
    p.ret = 0;
    return;
}
case 9: { // ID3D11Resource::GetEvictionPriority
    auto result = object->GetEvictionPriority();
    p.ret = result;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11SamplerState: {
    auto object = c.object<ID3D11SamplerState>(p.object, SD_COM_IF_ID3D11SamplerState);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11SamplerState::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11SamplerState::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11SamplerState::Release
    return c.Release(p);
}
case 3: { // ID3D11SamplerState::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11SamplerState::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11SamplerState::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11SamplerState::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
case 7: { // ID3D11SamplerState::GetDesc
    auto pDesc = c.write<D3D11_SAMPLER_DESC>(p.args[0], c.array_count(1));
    object->GetDesc(pDesc);
    p.ret = 0;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11ShaderResourceView: {
    auto object = c.object<ID3D11ShaderResourceView>(p.object, SD_COM_IF_ID3D11ShaderResourceView);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11ShaderResourceView::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11ShaderResourceView::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11ShaderResourceView::Release
    return c.Release(p);
}
case 3: { // ID3D11ShaderResourceView::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11ShaderResourceView::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11ShaderResourceView::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11ShaderResourceView::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
case 7: { // ID3D11ShaderResourceView::GetResource
    const uint32_t count_ppResource = c.array_count(1);
    auto guest_ppResource = c.write<uint32_t>(p.args[0], count_ppResource);
    if (guest_ppResource) std::fill_n(guest_ppResource, count_ppResource, 0u);
    std::vector<ID3D11Resource*> native_ppResource(count_ppResource, nullptr);
    auto ppResource = guest_ppResource ? native_ppResource.data() : nullptr;
    object->GetResource(ppResource);
    if (guest_ppResource) for (uint32_t i=0; i<count_ppResource; ++i) guest_ppResource[i] = c.adopt(native_ppResource[i], SD_COM_IF_ID3D11Resource);
    p.ret = 0;
    return;
}
case 8: { // ID3D11ShaderResourceView::GetDesc
    auto pDesc = c.write<D3D11_SHADER_RESOURCE_VIEW_DESC>(p.args[0], c.array_count(1));
    object->GetDesc(pDesc);
    p.ret = 0;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11Texture1D: {
    auto object = c.object<ID3D11Texture1D>(p.object, SD_COM_IF_ID3D11Texture1D);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11Texture1D::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11Texture1D::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11Texture1D::Release
    return c.Release(p);
}
case 3: { // ID3D11Texture1D::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11Texture1D::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11Texture1D::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11Texture1D::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
case 7: { // ID3D11Texture1D::GetType
    auto pResourceDimension = c.write<D3D11_RESOURCE_DIMENSION>(p.args[0], c.array_count(1));
    object->GetType(pResourceDimension);
    p.ret = 0;
    return;
}
case 8: { // ID3D11Texture1D::SetEvictionPriority
    auto EvictionPriority = (UINT)p.args[0];
    object->SetEvictionPriority(EvictionPriority);
    p.ret = 0;
    return;
}
case 9: { // ID3D11Texture1D::GetEvictionPriority
    auto result = object->GetEvictionPriority();
    p.ret = result;
    return;
}
case 10: { // ID3D11Texture1D::GetDesc
    auto pDesc = c.write<D3D11_TEXTURE1D_DESC>(p.args[0], c.array_count(1));
    object->GetDesc(pDesc);
    p.ret = 0;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11Texture2D: {
    auto object = c.object<ID3D11Texture2D>(p.object, SD_COM_IF_ID3D11Texture2D);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11Texture2D::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11Texture2D::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11Texture2D::Release
    return c.Release(p);
}
case 3: { // ID3D11Texture2D::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11Texture2D::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11Texture2D::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11Texture2D::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
case 7: { // ID3D11Texture2D::GetType
    auto pResourceDimension = c.write<D3D11_RESOURCE_DIMENSION>(p.args[0], c.array_count(1));
    object->GetType(pResourceDimension);
    p.ret = 0;
    return;
}
case 8: { // ID3D11Texture2D::SetEvictionPriority
    auto EvictionPriority = (UINT)p.args[0];
    object->SetEvictionPriority(EvictionPriority);
    p.ret = 0;
    return;
}
case 9: { // ID3D11Texture2D::GetEvictionPriority
    auto result = object->GetEvictionPriority();
    p.ret = result;
    return;
}
case 10: { // ID3D11Texture2D::GetDesc
    auto pDesc = c.write<D3D11_TEXTURE2D_DESC>(p.args[0], c.array_count(1));
    object->GetDesc(pDesc);
    p.ret = 0;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11Texture3D: {
    auto object = c.object<ID3D11Texture3D>(p.object, SD_COM_IF_ID3D11Texture3D);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11Texture3D::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11Texture3D::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11Texture3D::Release
    return c.Release(p);
}
case 3: { // ID3D11Texture3D::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11Texture3D::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11Texture3D::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11Texture3D::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
case 7: { // ID3D11Texture3D::GetType
    auto pResourceDimension = c.write<D3D11_RESOURCE_DIMENSION>(p.args[0], c.array_count(1));
    object->GetType(pResourceDimension);
    p.ret = 0;
    return;
}
case 8: { // ID3D11Texture3D::SetEvictionPriority
    auto EvictionPriority = (UINT)p.args[0];
    object->SetEvictionPriority(EvictionPriority);
    p.ret = 0;
    return;
}
case 9: { // ID3D11Texture3D::GetEvictionPriority
    auto result = object->GetEvictionPriority();
    p.ret = result;
    return;
}
case 10: { // ID3D11Texture3D::GetDesc
    auto pDesc = c.write<D3D11_TEXTURE3D_DESC>(p.args[0], c.array_count(1));
    object->GetDesc(pDesc);
    p.ret = 0;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11UnorderedAccessView: {
    auto object = c.object<ID3D11UnorderedAccessView>(p.object, SD_COM_IF_ID3D11UnorderedAccessView);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11UnorderedAccessView::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11UnorderedAccessView::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11UnorderedAccessView::Release
    return c.Release(p);
}
case 3: { // ID3D11UnorderedAccessView::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11UnorderedAccessView::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11UnorderedAccessView::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11UnorderedAccessView::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
case 7: { // ID3D11UnorderedAccessView::GetResource
    const uint32_t count_ppResource = c.array_count(1);
    auto guest_ppResource = c.write<uint32_t>(p.args[0], count_ppResource);
    if (guest_ppResource) std::fill_n(guest_ppResource, count_ppResource, 0u);
    std::vector<ID3D11Resource*> native_ppResource(count_ppResource, nullptr);
    auto ppResource = guest_ppResource ? native_ppResource.data() : nullptr;
    object->GetResource(ppResource);
    if (guest_ppResource) for (uint32_t i=0; i<count_ppResource; ++i) guest_ppResource[i] = c.adopt(native_ppResource[i], SD_COM_IF_ID3D11Resource);
    p.ret = 0;
    return;
}
case 8: { // ID3D11UnorderedAccessView::GetDesc
    auto pDesc = c.write<D3D11_UNORDERED_ACCESS_VIEW_DESC>(p.args[0], c.array_count(1));
    object->GetDesc(pDesc);
    p.ret = 0;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11VertexShader: {
    auto object = c.object<ID3D11VertexShader>(p.object, SD_COM_IF_ID3D11VertexShader);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11VertexShader::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11VertexShader::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11VertexShader::Release
    return c.Release(p);
}
case 3: { // ID3D11VertexShader::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11VertexShader::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11VertexShader::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11VertexShader::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_ID3D11View: {
    auto object = c.object<ID3D11View>(p.object, SD_COM_IF_ID3D11View);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // ID3D11View::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // ID3D11View::AddRef
    return c.AddRef(p);
}
case 2: { // ID3D11View::Release
    return c.Release(p);
}
case 3: { // ID3D11View::GetDevice
    const uint32_t count_ppDevice = c.array_count(1);
    auto guest_ppDevice = c.write<uint32_t>(p.args[0], count_ppDevice);
    if (guest_ppDevice) std::fill_n(guest_ppDevice, count_ppDevice, 0u);
    std::vector<ID3D11Device*> native_ppDevice(count_ppDevice, nullptr);
    auto ppDevice = guest_ppDevice ? native_ppDevice.data() : nullptr;
    object->GetDevice(ppDevice);
    if (guest_ppDevice) for (uint32_t i=0; i<count_ppDevice; ++i) guest_ppDevice[i] = c.adopt(native_ppDevice[i], SD_COM_IF_ID3D11Device);
    p.ret = 0;
    return;
}
case 4: { // ID3D11View::GetPrivateData
    return custom_ID3D11DeviceChild_GetPrivateData(c, object, p);
}
case 5: { // ID3D11View::SetPrivateData
    return custom_ID3D11DeviceChild_SetPrivateData(c, object, p);
}
case 6: { // ID3D11View::SetPrivateDataInterface
    return custom_ID3D11DeviceChild_SetPrivateDataInterface(c, object, p);
}
case 7: { // ID3D11View::GetResource
    const uint32_t count_ppResource = c.array_count(1);
    auto guest_ppResource = c.write<uint32_t>(p.args[0], count_ppResource);
    if (guest_ppResource) std::fill_n(guest_ppResource, count_ppResource, 0u);
    std::vector<ID3D11Resource*> native_ppResource(count_ppResource, nullptr);
    auto ppResource = guest_ppResource ? native_ppResource.data() : nullptr;
    object->GetResource(ppResource);
    if (guest_ppResource) for (uint32_t i=0; i<count_ppResource; ++i) guest_ppResource[i] = c.adopt(native_ppResource[i], SD_COM_IF_ID3D11Resource);
    p.ret = 0;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_IDXGIAdapter: {
    auto object = c.object<IDXGIAdapter>(p.object, SD_COM_IF_IDXGIAdapter);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // IDXGIAdapter::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // IDXGIAdapter::AddRef
    return c.AddRef(p);
}
case 2: { // IDXGIAdapter::Release
    return c.Release(p);
}
case 3: { // IDXGIAdapter::SetPrivateData
    return custom_IDXGIObject_SetPrivateData(c, object, p);
}
case 4: { // IDXGIAdapter::SetPrivateDataInterface
    return custom_IDXGIObject_SetPrivateDataInterface(c, object, p);
}
case 5: { // IDXGIAdapter::GetPrivateData
    return custom_IDXGIObject_GetPrivateData(c, object, p);
}
case 6: { // IDXGIAdapter::GetParent
    auto riid = *c.required_read<GUID>(p.args[0]);
    auto guest_parent = c.write<uint32_t>(p.args[1]);
    void *native_parent = nullptr;
    auto parent = guest_parent ? &native_parent : nullptr;
    auto result = object->GetParent(riid, parent);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_parent) *guest_parent = c.adopt((IUnknown*)native_parent, c.iid(riid));
    p.ret = result;
    return;
}
case 7: { // IDXGIAdapter::EnumOutputs
    auto output_idx = (UINT)p.args[0];
    const uint32_t count_output = c.array_count(1);
    auto guest_output = c.write<uint32_t>(p.args[1], count_output);
    if (guest_output) std::fill_n(guest_output, count_output, 0u);
    std::vector<IDXGIOutput*> native_output(count_output, nullptr);
    auto output = guest_output ? native_output.data() : nullptr;
    auto result = object->EnumOutputs(output_idx, output);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_output) for (uint32_t i=0; i<count_output; ++i) guest_output[i] = c.adopt(native_output[i], SD_COM_IF_IDXGIOutput);
    p.ret = result;
    return;
}
case 8: { // IDXGIAdapter::GetDesc
    return custom_IDXGIAdapter_GetDesc(c, object, p);
}
case 9: { // IDXGIAdapter::CheckInterfaceSupport
    auto guid = *c.required_read<GUID>(p.args[0]);
    auto umd_version = c.write<LARGE_INTEGER>(p.args[1], c.array_count(1));
    auto result = object->CheckInterfaceSupport(guid, umd_version);
    p.ret = result;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_IDXGIAdapter1: {
    auto object = c.object<IDXGIAdapter1>(p.object, SD_COM_IF_IDXGIAdapter1);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // IDXGIAdapter1::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // IDXGIAdapter1::AddRef
    return c.AddRef(p);
}
case 2: { // IDXGIAdapter1::Release
    return c.Release(p);
}
case 3: { // IDXGIAdapter1::SetPrivateData
    return custom_IDXGIObject_SetPrivateData(c, object, p);
}
case 4: { // IDXGIAdapter1::SetPrivateDataInterface
    return custom_IDXGIObject_SetPrivateDataInterface(c, object, p);
}
case 5: { // IDXGIAdapter1::GetPrivateData
    return custom_IDXGIObject_GetPrivateData(c, object, p);
}
case 6: { // IDXGIAdapter1::GetParent
    auto riid = *c.required_read<GUID>(p.args[0]);
    auto guest_parent = c.write<uint32_t>(p.args[1]);
    void *native_parent = nullptr;
    auto parent = guest_parent ? &native_parent : nullptr;
    auto result = object->GetParent(riid, parent);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_parent) *guest_parent = c.adopt((IUnknown*)native_parent, c.iid(riid));
    p.ret = result;
    return;
}
case 7: { // IDXGIAdapter1::EnumOutputs
    auto output_idx = (UINT)p.args[0];
    const uint32_t count_output = c.array_count(1);
    auto guest_output = c.write<uint32_t>(p.args[1], count_output);
    if (guest_output) std::fill_n(guest_output, count_output, 0u);
    std::vector<IDXGIOutput*> native_output(count_output, nullptr);
    auto output = guest_output ? native_output.data() : nullptr;
    auto result = object->EnumOutputs(output_idx, output);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_output) for (uint32_t i=0; i<count_output; ++i) guest_output[i] = c.adopt(native_output[i], SD_COM_IF_IDXGIOutput);
    p.ret = result;
    return;
}
case 8: { // IDXGIAdapter1::GetDesc
    return custom_IDXGIAdapter_GetDesc(c, object, p);
}
case 9: { // IDXGIAdapter1::CheckInterfaceSupport
    auto guid = *c.required_read<GUID>(p.args[0]);
    auto umd_version = c.write<LARGE_INTEGER>(p.args[1], c.array_count(1));
    auto result = object->CheckInterfaceSupport(guid, umd_version);
    p.ret = result;
    return;
}
case 10: { // IDXGIAdapter1::GetDesc1
    return custom_IDXGIAdapter1_GetDesc1(c, object, p);
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_IDXGIDevice: {
    auto object = c.object<IDXGIDevice>(p.object, SD_COM_IF_IDXGIDevice);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // IDXGIDevice::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // IDXGIDevice::AddRef
    return c.AddRef(p);
}
case 2: { // IDXGIDevice::Release
    return c.Release(p);
}
case 3: { // IDXGIDevice::SetPrivateData
    return custom_IDXGIObject_SetPrivateData(c, object, p);
}
case 4: { // IDXGIDevice::SetPrivateDataInterface
    return custom_IDXGIObject_SetPrivateDataInterface(c, object, p);
}
case 5: { // IDXGIDevice::GetPrivateData
    return custom_IDXGIObject_GetPrivateData(c, object, p);
}
case 6: { // IDXGIDevice::GetParent
    auto riid = *c.required_read<GUID>(p.args[0]);
    auto guest_parent = c.write<uint32_t>(p.args[1]);
    void *native_parent = nullptr;
    auto parent = guest_parent ? &native_parent : nullptr;
    auto result = object->GetParent(riid, parent);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_parent) *guest_parent = c.adopt((IUnknown*)native_parent, c.iid(riid));
    p.ret = result;
    return;
}
case 7: { // IDXGIDevice::GetAdapter
    const uint32_t count_adapter = c.array_count(1);
    auto guest_adapter = c.write<uint32_t>(p.args[0], count_adapter);
    if (guest_adapter) std::fill_n(guest_adapter, count_adapter, 0u);
    std::vector<IDXGIAdapter*> native_adapter(count_adapter, nullptr);
    auto adapter = guest_adapter ? native_adapter.data() : nullptr;
    auto result = object->GetAdapter(adapter);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_adapter) for (uint32_t i=0; i<count_adapter; ++i) guest_adapter[i] = c.adopt(native_adapter[i], SD_COM_IF_IDXGIAdapter);
    p.ret = result;
    return;
}
case 8: { // IDXGIDevice::CreateSurface
    return c.unsupported(p, "IDXGIDevice::CreateSurface");
}
case 9: { // IDXGIDevice::QueryResourceResidency
    auto resource_count = (UINT)p.args[2];
    const uint32_t count_resources = c.array_count(1);
    auto tokens_resources = c.read<uint32_t>(p.args[0], count_resources);
    std::vector<IUnknown*> native_resources(tokens_resources ? count_resources : 0);
    for (uint32_t i=0; i<native_resources.size(); ++i) native_resources[i] = c.object<IUnknown>(tokens_resources[i], SD_COM_IF_IUnknown);
    auto resources = tokens_resources ? native_resources.data() : nullptr;
    auto residency = c.write<DXGI_RESIDENCY>(p.args[1], c.array_count(1));
    auto result = object->QueryResourceResidency(resources, residency, resource_count);
    p.ret = result;
    return;
}
case 10: { // IDXGIDevice::SetGPUThreadPriority
    auto priority = (INT)p.args[0];
    auto result = object->SetGPUThreadPriority(priority);
    p.ret = result;
    return;
}
case 11: { // IDXGIDevice::GetGPUThreadPriority
    auto priority = c.write<INT>(p.args[0], c.array_count(1));
    auto result = object->GetGPUThreadPriority(priority);
    p.ret = result;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_IDXGIDevice1: {
    auto object = c.object<IDXGIDevice1>(p.object, SD_COM_IF_IDXGIDevice1);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // IDXGIDevice1::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // IDXGIDevice1::AddRef
    return c.AddRef(p);
}
case 2: { // IDXGIDevice1::Release
    return c.Release(p);
}
case 3: { // IDXGIDevice1::SetPrivateData
    return custom_IDXGIObject_SetPrivateData(c, object, p);
}
case 4: { // IDXGIDevice1::SetPrivateDataInterface
    return custom_IDXGIObject_SetPrivateDataInterface(c, object, p);
}
case 5: { // IDXGIDevice1::GetPrivateData
    return custom_IDXGIObject_GetPrivateData(c, object, p);
}
case 6: { // IDXGIDevice1::GetParent
    auto riid = *c.required_read<GUID>(p.args[0]);
    auto guest_parent = c.write<uint32_t>(p.args[1]);
    void *native_parent = nullptr;
    auto parent = guest_parent ? &native_parent : nullptr;
    auto result = object->GetParent(riid, parent);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_parent) *guest_parent = c.adopt((IUnknown*)native_parent, c.iid(riid));
    p.ret = result;
    return;
}
case 7: { // IDXGIDevice1::GetAdapter
    const uint32_t count_adapter = c.array_count(1);
    auto guest_adapter = c.write<uint32_t>(p.args[0], count_adapter);
    if (guest_adapter) std::fill_n(guest_adapter, count_adapter, 0u);
    std::vector<IDXGIAdapter*> native_adapter(count_adapter, nullptr);
    auto adapter = guest_adapter ? native_adapter.data() : nullptr;
    auto result = object->GetAdapter(adapter);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_adapter) for (uint32_t i=0; i<count_adapter; ++i) guest_adapter[i] = c.adopt(native_adapter[i], SD_COM_IF_IDXGIAdapter);
    p.ret = result;
    return;
}
case 8: { // IDXGIDevice1::CreateSurface
    return c.unsupported(p, "IDXGIDevice1::CreateSurface");
}
case 9: { // IDXGIDevice1::QueryResourceResidency
    auto resource_count = (UINT)p.args[2];
    const uint32_t count_resources = c.array_count(1);
    auto tokens_resources = c.read<uint32_t>(p.args[0], count_resources);
    std::vector<IUnknown*> native_resources(tokens_resources ? count_resources : 0);
    for (uint32_t i=0; i<native_resources.size(); ++i) native_resources[i] = c.object<IUnknown>(tokens_resources[i], SD_COM_IF_IUnknown);
    auto resources = tokens_resources ? native_resources.data() : nullptr;
    auto residency = c.write<DXGI_RESIDENCY>(p.args[1], c.array_count(1));
    auto result = object->QueryResourceResidency(resources, residency, resource_count);
    p.ret = result;
    return;
}
case 10: { // IDXGIDevice1::SetGPUThreadPriority
    auto priority = (INT)p.args[0];
    auto result = object->SetGPUThreadPriority(priority);
    p.ret = result;
    return;
}
case 11: { // IDXGIDevice1::GetGPUThreadPriority
    auto priority = c.write<INT>(p.args[0], c.array_count(1));
    auto result = object->GetGPUThreadPriority(priority);
    p.ret = result;
    return;
}
case 12: { // IDXGIDevice1::SetMaximumFrameLatency
    auto MaxLatency = (UINT)p.args[0];
    auto result = object->SetMaximumFrameLatency(MaxLatency);
    p.ret = result;
    return;
}
case 13: { // IDXGIDevice1::GetMaximumFrameLatency
    auto pMaxLatency = c.write<UINT>(p.args[0], c.array_count(1));
    auto result = object->GetMaximumFrameLatency(pMaxLatency);
    p.ret = result;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_IDXGIDeviceSubObject: {
    auto object = c.object<IDXGIDeviceSubObject>(p.object, SD_COM_IF_IDXGIDeviceSubObject);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // IDXGIDeviceSubObject::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // IDXGIDeviceSubObject::AddRef
    return c.AddRef(p);
}
case 2: { // IDXGIDeviceSubObject::Release
    return c.Release(p);
}
case 3: { // IDXGIDeviceSubObject::SetPrivateData
    return custom_IDXGIObject_SetPrivateData(c, object, p);
}
case 4: { // IDXGIDeviceSubObject::SetPrivateDataInterface
    return custom_IDXGIObject_SetPrivateDataInterface(c, object, p);
}
case 5: { // IDXGIDeviceSubObject::GetPrivateData
    return custom_IDXGIObject_GetPrivateData(c, object, p);
}
case 6: { // IDXGIDeviceSubObject::GetParent
    auto riid = *c.required_read<GUID>(p.args[0]);
    auto guest_parent = c.write<uint32_t>(p.args[1]);
    void *native_parent = nullptr;
    auto parent = guest_parent ? &native_parent : nullptr;
    auto result = object->GetParent(riid, parent);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_parent) *guest_parent = c.adopt((IUnknown*)native_parent, c.iid(riid));
    p.ret = result;
    return;
}
case 7: { // IDXGIDeviceSubObject::GetDevice
    auto riid = *c.required_read<GUID>(p.args[0]);
    auto guest_device = c.write<uint32_t>(p.args[1]);
    void *native_device = nullptr;
    auto device = guest_device ? &native_device : nullptr;
    auto result = object->GetDevice(riid, device);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_device) *guest_device = c.adopt((IUnknown*)native_device, c.iid(riid));
    p.ret = result;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_IDXGIFactory: {
    auto object = c.object<IDXGIFactory>(p.object, SD_COM_IF_IDXGIFactory);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // IDXGIFactory::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // IDXGIFactory::AddRef
    return c.AddRef(p);
}
case 2: { // IDXGIFactory::Release
    return c.Release(p);
}
case 3: { // IDXGIFactory::SetPrivateData
    return custom_IDXGIObject_SetPrivateData(c, object, p);
}
case 4: { // IDXGIFactory::SetPrivateDataInterface
    return custom_IDXGIObject_SetPrivateDataInterface(c, object, p);
}
case 5: { // IDXGIFactory::GetPrivateData
    return custom_IDXGIObject_GetPrivateData(c, object, p);
}
case 6: { // IDXGIFactory::GetParent
    auto riid = *c.required_read<GUID>(p.args[0]);
    auto guest_parent = c.write<uint32_t>(p.args[1]);
    void *native_parent = nullptr;
    auto parent = guest_parent ? &native_parent : nullptr;
    auto result = object->GetParent(riid, parent);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_parent) *guest_parent = c.adopt((IUnknown*)native_parent, c.iid(riid));
    p.ret = result;
    return;
}
case 7: { // IDXGIFactory::EnumAdapters
    auto adapter_idx = (UINT)p.args[0];
    const uint32_t count_adapter = c.array_count(1);
    auto guest_adapter = c.write<uint32_t>(p.args[1], count_adapter);
    if (guest_adapter) std::fill_n(guest_adapter, count_adapter, 0u);
    std::vector<IDXGIAdapter*> native_adapter(count_adapter, nullptr);
    auto adapter = guest_adapter ? native_adapter.data() : nullptr;
    auto result = object->EnumAdapters(adapter_idx, adapter);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_adapter) for (uint32_t i=0; i<count_adapter; ++i) guest_adapter[i] = c.adopt(native_adapter[i], SD_COM_IF_IDXGIAdapter);
    p.ret = result;
    return;
}
case 8: { // IDXGIFactory::MakeWindowAssociation
    return custom_IDXGIFactory_MakeWindowAssociation(c, object, p);
}
case 9: { // IDXGIFactory::GetWindowAssociation
    return custom_IDXGIFactory_GetWindowAssociation(c, object, p);
}
case 10: { // IDXGIFactory::CreateSwapChain
    return custom_IDXGIFactory_CreateSwapChain(c, object, p);
}
case 11: { // IDXGIFactory::CreateSoftwareAdapter
    return c.unsupported(p, "IDXGIFactory::CreateSoftwareAdapter");
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_IDXGIFactory1: {
    auto object = c.object<IDXGIFactory1>(p.object, SD_COM_IF_IDXGIFactory1);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // IDXGIFactory1::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // IDXGIFactory1::AddRef
    return c.AddRef(p);
}
case 2: { // IDXGIFactory1::Release
    return c.Release(p);
}
case 3: { // IDXGIFactory1::SetPrivateData
    return custom_IDXGIObject_SetPrivateData(c, object, p);
}
case 4: { // IDXGIFactory1::SetPrivateDataInterface
    return custom_IDXGIObject_SetPrivateDataInterface(c, object, p);
}
case 5: { // IDXGIFactory1::GetPrivateData
    return custom_IDXGIObject_GetPrivateData(c, object, p);
}
case 6: { // IDXGIFactory1::GetParent
    auto riid = *c.required_read<GUID>(p.args[0]);
    auto guest_parent = c.write<uint32_t>(p.args[1]);
    void *native_parent = nullptr;
    auto parent = guest_parent ? &native_parent : nullptr;
    auto result = object->GetParent(riid, parent);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_parent) *guest_parent = c.adopt((IUnknown*)native_parent, c.iid(riid));
    p.ret = result;
    return;
}
case 7: { // IDXGIFactory1::EnumAdapters
    auto adapter_idx = (UINT)p.args[0];
    const uint32_t count_adapter = c.array_count(1);
    auto guest_adapter = c.write<uint32_t>(p.args[1], count_adapter);
    if (guest_adapter) std::fill_n(guest_adapter, count_adapter, 0u);
    std::vector<IDXGIAdapter*> native_adapter(count_adapter, nullptr);
    auto adapter = guest_adapter ? native_adapter.data() : nullptr;
    auto result = object->EnumAdapters(adapter_idx, adapter);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_adapter) for (uint32_t i=0; i<count_adapter; ++i) guest_adapter[i] = c.adopt(native_adapter[i], SD_COM_IF_IDXGIAdapter);
    p.ret = result;
    return;
}
case 8: { // IDXGIFactory1::MakeWindowAssociation
    return custom_IDXGIFactory_MakeWindowAssociation(c, object, p);
}
case 9: { // IDXGIFactory1::GetWindowAssociation
    return custom_IDXGIFactory_GetWindowAssociation(c, object, p);
}
case 10: { // IDXGIFactory1::CreateSwapChain
    return custom_IDXGIFactory_CreateSwapChain(c, object, p);
}
case 11: { // IDXGIFactory1::CreateSoftwareAdapter
    return c.unsupported(p, "IDXGIFactory1::CreateSoftwareAdapter");
}
case 12: { // IDXGIFactory1::EnumAdapters1
    auto Adapter = (UINT)p.args[0];
    const uint32_t count_ppAdapter = c.array_count(1);
    auto guest_ppAdapter = c.write<uint32_t>(p.args[1], count_ppAdapter);
    if (guest_ppAdapter) std::fill_n(guest_ppAdapter, count_ppAdapter, 0u);
    std::vector<IDXGIAdapter1*> native_ppAdapter(count_ppAdapter, nullptr);
    auto ppAdapter = guest_ppAdapter ? native_ppAdapter.data() : nullptr;
    auto result = object->EnumAdapters1(Adapter, ppAdapter);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_ppAdapter) for (uint32_t i=0; i<count_ppAdapter; ++i) guest_ppAdapter[i] = c.adopt(native_ppAdapter[i], SD_COM_IF_IDXGIAdapter1);
    p.ret = result;
    return;
}
case 13: { // IDXGIFactory1::IsCurrent
    auto result = object->IsCurrent();
    p.ret = result;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_IDXGIKeyedMutex: {
    auto object = c.object<IDXGIKeyedMutex>(p.object, SD_COM_IF_IDXGIKeyedMutex);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // IDXGIKeyedMutex::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // IDXGIKeyedMutex::AddRef
    return c.AddRef(p);
}
case 2: { // IDXGIKeyedMutex::Release
    return c.Release(p);
}
case 3: { // IDXGIKeyedMutex::SetPrivateData
    return custom_IDXGIObject_SetPrivateData(c, object, p);
}
case 4: { // IDXGIKeyedMutex::SetPrivateDataInterface
    return custom_IDXGIObject_SetPrivateDataInterface(c, object, p);
}
case 5: { // IDXGIKeyedMutex::GetPrivateData
    return custom_IDXGIObject_GetPrivateData(c, object, p);
}
case 6: { // IDXGIKeyedMutex::GetParent
    auto riid = *c.required_read<GUID>(p.args[0]);
    auto guest_parent = c.write<uint32_t>(p.args[1]);
    void *native_parent = nullptr;
    auto parent = guest_parent ? &native_parent : nullptr;
    auto result = object->GetParent(riid, parent);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_parent) *guest_parent = c.adopt((IUnknown*)native_parent, c.iid(riid));
    p.ret = result;
    return;
}
case 7: { // IDXGIKeyedMutex::GetDevice
    auto riid = *c.required_read<GUID>(p.args[0]);
    auto guest_device = c.write<uint32_t>(p.args[1]);
    void *native_device = nullptr;
    auto device = guest_device ? &native_device : nullptr;
    auto result = object->GetDevice(riid, device);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_device) *guest_device = c.adopt((IUnknown*)native_device, c.iid(riid));
    p.ret = result;
    return;
}
case 8: { // IDXGIKeyedMutex::AcquireSync
    auto Key = uint64_t(p.args[0]) | uint64_t(p.high[0])<<32;
    auto dwMilliseconds = (DWORD)p.args[1];
    auto result = object->AcquireSync(Key, dwMilliseconds);
    p.ret = result;
    return;
}
case 9: { // IDXGIKeyedMutex::ReleaseSync
    auto Key = uint64_t(p.args[0]) | uint64_t(p.high[0])<<32;
    auto result = object->ReleaseSync(Key);
    p.ret = result;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_IDXGIObject: {
    auto object = c.object<IDXGIObject>(p.object, SD_COM_IF_IDXGIObject);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // IDXGIObject::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // IDXGIObject::AddRef
    return c.AddRef(p);
}
case 2: { // IDXGIObject::Release
    return c.Release(p);
}
case 3: { // IDXGIObject::SetPrivateData
    return custom_IDXGIObject_SetPrivateData(c, object, p);
}
case 4: { // IDXGIObject::SetPrivateDataInterface
    return custom_IDXGIObject_SetPrivateDataInterface(c, object, p);
}
case 5: { // IDXGIObject::GetPrivateData
    return custom_IDXGIObject_GetPrivateData(c, object, p);
}
case 6: { // IDXGIObject::GetParent
    auto riid = *c.required_read<GUID>(p.args[0]);
    auto guest_parent = c.write<uint32_t>(p.args[1]);
    void *native_parent = nullptr;
    auto parent = guest_parent ? &native_parent : nullptr;
    auto result = object->GetParent(riid, parent);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_parent) *guest_parent = c.adopt((IUnknown*)native_parent, c.iid(riid));
    p.ret = result;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_IDXGIOutput: {
    auto object = c.object<IDXGIOutput>(p.object, SD_COM_IF_IDXGIOutput);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // IDXGIOutput::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // IDXGIOutput::AddRef
    return c.AddRef(p);
}
case 2: { // IDXGIOutput::Release
    return c.Release(p);
}
case 3: { // IDXGIOutput::SetPrivateData
    return custom_IDXGIObject_SetPrivateData(c, object, p);
}
case 4: { // IDXGIOutput::SetPrivateDataInterface
    return custom_IDXGIObject_SetPrivateDataInterface(c, object, p);
}
case 5: { // IDXGIOutput::GetPrivateData
    return custom_IDXGIObject_GetPrivateData(c, object, p);
}
case 6: { // IDXGIOutput::GetParent
    auto riid = *c.required_read<GUID>(p.args[0]);
    auto guest_parent = c.write<uint32_t>(p.args[1]);
    void *native_parent = nullptr;
    auto parent = guest_parent ? &native_parent : nullptr;
    auto result = object->GetParent(riid, parent);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_parent) *guest_parent = c.adopt((IUnknown*)native_parent, c.iid(riid));
    p.ret = result;
    return;
}
case 7: { // IDXGIOutput::GetDesc
    return custom_IDXGIOutput_GetDesc(c, object, p);
}
case 8: { // IDXGIOutput::GetDisplayModeList
    auto format = (DXGI_FORMAT)p.args[0];
    auto flags = (UINT)p.args[1];
    auto mode_count = c.write<UINT>(p.args[2], c.array_count(1));
    auto desc = c.write<DXGI_MODE_DESC>(p.args[3], c.array_count((mode_count ? *mode_count : 0)));
    auto result = object->GetDisplayModeList(format, flags, mode_count, desc);
    p.ret = result;
    return;
}
case 9: { // IDXGIOutput::FindClosestMatchingMode
    auto mode = c.read<DXGI_MODE_DESC>(p.args[0], c.array_count(1));
    auto closest_match = c.write<DXGI_MODE_DESC>(p.args[1], c.array_count(1));
    auto device = c.object<IUnknown>(p.args[2], SD_COM_IF_IUnknown);
    auto result = object->FindClosestMatchingMode(mode, closest_match, device);
    p.ret = result;
    return;
}
case 10: { // IDXGIOutput::WaitForVBlank
    auto result = object->WaitForVBlank();
    p.ret = result;
    return;
}
case 11: { // IDXGIOutput::TakeOwnership
    auto exclusive = (WINBOOL)p.args[1];
    auto device = c.object<IUnknown>(p.args[0], SD_COM_IF_IUnknown);
    auto result = object->TakeOwnership(device, exclusive);
    p.ret = result;
    return;
}
case 12: { // IDXGIOutput::ReleaseOwnership
    object->ReleaseOwnership();
    p.ret = 0;
    return;
}
case 13: { // IDXGIOutput::GetGammaControlCapabilities
    auto gamma_caps = c.write<DXGI_GAMMA_CONTROL_CAPABILITIES>(p.args[0], c.array_count(1));
    auto result = object->GetGammaControlCapabilities(gamma_caps);
    p.ret = result;
    return;
}
case 14: { // IDXGIOutput::SetGammaControl
    auto gamma_control = c.read<DXGI_GAMMA_CONTROL>(p.args[0], c.array_count(1));
    auto result = object->SetGammaControl(gamma_control);
    p.ret = result;
    return;
}
case 15: { // IDXGIOutput::GetGammaControl
    auto gamma_control = c.write<DXGI_GAMMA_CONTROL>(p.args[0], c.array_count(1));
    auto result = object->GetGammaControl(gamma_control);
    p.ret = result;
    return;
}
case 16: { // IDXGIOutput::SetDisplaySurface
    auto surface = c.object<IDXGISurface>(p.args[0], SD_COM_IF_IDXGISurface);
    auto result = object->SetDisplaySurface(surface);
    p.ret = result;
    return;
}
case 17: { // IDXGIOutput::GetDisplaySurfaceData
    auto surface = c.object<IDXGISurface>(p.args[0], SD_COM_IF_IDXGISurface);
    auto result = object->GetDisplaySurfaceData(surface);
    p.ret = result;
    return;
}
case 18: { // IDXGIOutput::GetFrameStatistics
    auto stats = c.write<DXGI_FRAME_STATISTICS>(p.args[0], c.array_count(1));
    auto result = object->GetFrameStatistics(stats);
    p.ret = result;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_IDXGIResource: {
    auto object = c.object<IDXGIResource>(p.object, SD_COM_IF_IDXGIResource);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // IDXGIResource::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // IDXGIResource::AddRef
    return c.AddRef(p);
}
case 2: { // IDXGIResource::Release
    return c.Release(p);
}
case 3: { // IDXGIResource::SetPrivateData
    return custom_IDXGIObject_SetPrivateData(c, object, p);
}
case 4: { // IDXGIResource::SetPrivateDataInterface
    return custom_IDXGIObject_SetPrivateDataInterface(c, object, p);
}
case 5: { // IDXGIResource::GetPrivateData
    return custom_IDXGIObject_GetPrivateData(c, object, p);
}
case 6: { // IDXGIResource::GetParent
    auto riid = *c.required_read<GUID>(p.args[0]);
    auto guest_parent = c.write<uint32_t>(p.args[1]);
    void *native_parent = nullptr;
    auto parent = guest_parent ? &native_parent : nullptr;
    auto result = object->GetParent(riid, parent);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_parent) *guest_parent = c.adopt((IUnknown*)native_parent, c.iid(riid));
    p.ret = result;
    return;
}
case 7: { // IDXGIResource::GetDevice
    auto riid = *c.required_read<GUID>(p.args[0]);
    auto guest_device = c.write<uint32_t>(p.args[1]);
    void *native_device = nullptr;
    auto device = guest_device ? &native_device : nullptr;
    auto result = object->GetDevice(riid, device);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_device) *guest_device = c.adopt((IUnknown*)native_device, c.iid(riid));
    p.ret = result;
    return;
}
case 8: { // IDXGIResource::GetSharedHandle
    return c.unsupported(p, "IDXGIResource::GetSharedHandle");
}
case 9: { // IDXGIResource::GetUsage
    auto pUsage = c.write<DXGI_USAGE>(p.args[0], c.array_count(1));
    auto result = object->GetUsage(pUsage);
    p.ret = result;
    return;
}
case 10: { // IDXGIResource::SetEvictionPriority
    auto EvictionPriority = (UINT)p.args[0];
    auto result = object->SetEvictionPriority(EvictionPriority);
    p.ret = result;
    return;
}
case 11: { // IDXGIResource::GetEvictionPriority
    auto pEvictionPriority = c.write<UINT>(p.args[0], c.array_count(1));
    auto result = object->GetEvictionPriority(pEvictionPriority);
    p.ret = result;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_IDXGISurface: {
    auto object = c.object<IDXGISurface>(p.object, SD_COM_IF_IDXGISurface);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // IDXGISurface::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // IDXGISurface::AddRef
    return c.AddRef(p);
}
case 2: { // IDXGISurface::Release
    return c.Release(p);
}
case 3: { // IDXGISurface::SetPrivateData
    return custom_IDXGIObject_SetPrivateData(c, object, p);
}
case 4: { // IDXGISurface::SetPrivateDataInterface
    return custom_IDXGIObject_SetPrivateDataInterface(c, object, p);
}
case 5: { // IDXGISurface::GetPrivateData
    return custom_IDXGIObject_GetPrivateData(c, object, p);
}
case 6: { // IDXGISurface::GetParent
    auto riid = *c.required_read<GUID>(p.args[0]);
    auto guest_parent = c.write<uint32_t>(p.args[1]);
    void *native_parent = nullptr;
    auto parent = guest_parent ? &native_parent : nullptr;
    auto result = object->GetParent(riid, parent);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_parent) *guest_parent = c.adopt((IUnknown*)native_parent, c.iid(riid));
    p.ret = result;
    return;
}
case 7: { // IDXGISurface::GetDevice
    auto riid = *c.required_read<GUID>(p.args[0]);
    auto guest_device = c.write<uint32_t>(p.args[1]);
    void *native_device = nullptr;
    auto device = guest_device ? &native_device : nullptr;
    auto result = object->GetDevice(riid, device);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_device) *guest_device = c.adopt((IUnknown*)native_device, c.iid(riid));
    p.ret = result;
    return;
}
case 8: { // IDXGISurface::GetDesc
    auto desc = c.write<DXGI_SURFACE_DESC>(p.args[0], c.array_count(1));
    auto result = object->GetDesc(desc);
    p.ret = result;
    return;
}
case 9: { // IDXGISurface::Map
    return custom_IDXGISurface_Map(c, object, p);
}
case 10: { // IDXGISurface::Unmap
    return custom_IDXGISurface_Unmap(c, object, p);
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_IDXGISurface1: {
    auto object = c.object<IDXGISurface1>(p.object, SD_COM_IF_IDXGISurface1);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // IDXGISurface1::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // IDXGISurface1::AddRef
    return c.AddRef(p);
}
case 2: { // IDXGISurface1::Release
    return c.Release(p);
}
case 3: { // IDXGISurface1::SetPrivateData
    return custom_IDXGIObject_SetPrivateData(c, object, p);
}
case 4: { // IDXGISurface1::SetPrivateDataInterface
    return custom_IDXGIObject_SetPrivateDataInterface(c, object, p);
}
case 5: { // IDXGISurface1::GetPrivateData
    return custom_IDXGIObject_GetPrivateData(c, object, p);
}
case 6: { // IDXGISurface1::GetParent
    auto riid = *c.required_read<GUID>(p.args[0]);
    auto guest_parent = c.write<uint32_t>(p.args[1]);
    void *native_parent = nullptr;
    auto parent = guest_parent ? &native_parent : nullptr;
    auto result = object->GetParent(riid, parent);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_parent) *guest_parent = c.adopt((IUnknown*)native_parent, c.iid(riid));
    p.ret = result;
    return;
}
case 7: { // IDXGISurface1::GetDevice
    auto riid = *c.required_read<GUID>(p.args[0]);
    auto guest_device = c.write<uint32_t>(p.args[1]);
    void *native_device = nullptr;
    auto device = guest_device ? &native_device : nullptr;
    auto result = object->GetDevice(riid, device);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_device) *guest_device = c.adopt((IUnknown*)native_device, c.iid(riid));
    p.ret = result;
    return;
}
case 8: { // IDXGISurface1::GetDesc
    auto desc = c.write<DXGI_SURFACE_DESC>(p.args[0], c.array_count(1));
    auto result = object->GetDesc(desc);
    p.ret = result;
    return;
}
case 9: { // IDXGISurface1::Map
    return custom_IDXGISurface_Map(c, object, p);
}
case 10: { // IDXGISurface1::Unmap
    return custom_IDXGISurface_Unmap(c, object, p);
}
case 11: { // IDXGISurface1::GetDC
    return c.unsupported(p, "IDXGISurface1::GetDC");
}
case 12: { // IDXGISurface1::ReleaseDC
    return c.unsupported(p, "IDXGISurface1::ReleaseDC");
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_IDXGISwapChain: {
    auto object = c.object<IDXGISwapChain>(p.object, SD_COM_IF_IDXGISwapChain);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // IDXGISwapChain::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // IDXGISwapChain::AddRef
    return c.AddRef(p);
}
case 2: { // IDXGISwapChain::Release
    return c.Release(p);
}
case 3: { // IDXGISwapChain::SetPrivateData
    return custom_IDXGIObject_SetPrivateData(c, object, p);
}
case 4: { // IDXGISwapChain::SetPrivateDataInterface
    return custom_IDXGIObject_SetPrivateDataInterface(c, object, p);
}
case 5: { // IDXGISwapChain::GetPrivateData
    return custom_IDXGIObject_GetPrivateData(c, object, p);
}
case 6: { // IDXGISwapChain::GetParent
    auto riid = *c.required_read<GUID>(p.args[0]);
    auto guest_parent = c.write<uint32_t>(p.args[1]);
    void *native_parent = nullptr;
    auto parent = guest_parent ? &native_parent : nullptr;
    auto result = object->GetParent(riid, parent);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_parent) *guest_parent = c.adopt((IUnknown*)native_parent, c.iid(riid));
    p.ret = result;
    return;
}
case 7: { // IDXGISwapChain::GetDevice
    auto riid = *c.required_read<GUID>(p.args[0]);
    auto guest_device = c.write<uint32_t>(p.args[1]);
    void *native_device = nullptr;
    auto device = guest_device ? &native_device : nullptr;
    auto result = object->GetDevice(riid, device);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_device) *guest_device = c.adopt((IUnknown*)native_device, c.iid(riid));
    p.ret = result;
    return;
}
case 8: { // IDXGISwapChain::Present
    return custom_IDXGISwapChain_Present(c, object, p);
}
case 9: { // IDXGISwapChain::GetBuffer
    auto buffer_idx = (UINT)p.args[0];
    auto riid = *c.required_read<GUID>(p.args[1]);
    auto guest_surface = c.write<uint32_t>(p.args[2]);
    void *native_surface = nullptr;
    auto surface = guest_surface ? &native_surface : nullptr;
    auto result = object->GetBuffer(buffer_idx, riid, surface);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_surface) *guest_surface = c.adopt((IUnknown*)native_surface, c.iid(riid));
    p.ret = result;
    return;
}
case 10: { // IDXGISwapChain::SetFullscreenState
    return custom_IDXGISwapChain_SetFullscreenState(c, object, p);
}
case 11: { // IDXGISwapChain::GetFullscreenState
    return custom_IDXGISwapChain_GetFullscreenState(c, object, p);
}
case 12: { // IDXGISwapChain::GetDesc
    return custom_IDXGISwapChain_GetDesc(c, object, p);
}
case 13: { // IDXGISwapChain::ResizeBuffers
    return custom_IDXGISwapChain_ResizeBuffers(c, object, p);
}
case 14: { // IDXGISwapChain::ResizeTarget
    auto target_mode_desc = c.read<DXGI_MODE_DESC>(p.args[0], c.array_count(1));
    auto result = object->ResizeTarget(target_mode_desc);
    p.ret = result;
    return;
}
case 15: { // IDXGISwapChain::GetContainingOutput
    const uint32_t count_output = c.array_count(1);
    auto guest_output = c.write<uint32_t>(p.args[0], count_output);
    if (guest_output) std::fill_n(guest_output, count_output, 0u);
    std::vector<IDXGIOutput*> native_output(count_output, nullptr);
    auto output = guest_output ? native_output.data() : nullptr;
    auto result = object->GetContainingOutput(output);
    if (FAILED(result)) { p.ret = result; return; }
    if (guest_output) for (uint32_t i=0; i<count_output; ++i) guest_output[i] = c.adopt(native_output[i], SD_COM_IF_IDXGIOutput);
    p.ret = result;
    return;
}
case 16: { // IDXGISwapChain::GetFrameStatistics
    auto stats = c.write<DXGI_FRAME_STATISTICS>(p.args[0], c.array_count(1));
    auto result = object->GetFrameStatistics(stats);
    p.ret = result;
    return;
}
case 17: { // IDXGISwapChain::GetLastPresentCount
    auto last_present_count = c.write<UINT>(p.args[0], c.array_count(1));
    auto result = object->GetLastPresentCount(last_present_count);
    p.ret = result;
    return;
}
    default: return c.unsupported(p, "invalid method index");
    }
}
case SD_COM_IF_IUnknown: {
    auto object = c.object<IUnknown>(p.object, SD_COM_IF_IUnknown);
    if (!object) throw Fault(E_POINTER);
    switch (p.method) {
case 0: { // IUnknown::QueryInterface
    return c.QueryInterface(p);
}
case 1: { // IUnknown::AddRef
    return c.AddRef(p);
}
case 2: { // IUnknown::Release
    return c.Release(p);
}
    default: return c.unsupported(p, "invalid method index");
    }
}
