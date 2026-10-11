static HRESULT STDMETHODCALLTYPE g_ID3D10Multithread_QueryInterface(ID3D10Multithread *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D10Multithread_AddRef(ID3D10Multithread *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D10Multithread_Release(ID3D10Multithread *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D10Multithread_Enter(ID3D10Multithread *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D10Multithread, 3};
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D10Multithread_Leave(ID3D10Multithread *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D10Multithread, 4};
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static WINBOOL STDMETHODCALLTYPE g_ID3D10Multithread_SetMultithreadProtected(ID3D10Multithread *This, WINBOOL bMTProtect) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D10Multithread, 5};
    packet.args[0] = (uint32_t)bMTProtect;
    LONG status = proxy_call(&packet);
    if (status < 0) { return (WINBOOL)status; }
    return (WINBOOL)packet.ret;
}
static WINBOOL STDMETHODCALLTYPE g_ID3D10Multithread_GetMultithreadProtected(ID3D10Multithread *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D10Multithread, 6};
    LONG status = proxy_call(&packet);
    if (status < 0) { return (WINBOOL)status; }
    return (WINBOOL)packet.ret;
}
static const ID3D10MultithreadVtbl vtbl_ID3D10Multithread = {
    g_ID3D10Multithread_QueryInterface,
    g_ID3D10Multithread_AddRef,
    g_ID3D10Multithread_Release,
    g_ID3D10Multithread_Enter,
    g_ID3D10Multithread_Leave,
    g_ID3D10Multithread_SetMultithreadProtected,
    g_ID3D10Multithread_GetMultithreadProtected
};
static HRESULT STDMETHODCALLTYPE g_ID3D11Asynchronous_QueryInterface(ID3D11Asynchronous *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11Asynchronous_AddRef(ID3D11Asynchronous *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11Asynchronous_Release(ID3D11Asynchronous *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11Asynchronous_GetDevice(ID3D11Asynchronous *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Asynchronous, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Asynchronous_GetPrivateData(ID3D11Asynchronous *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Asynchronous_SetPrivateData(ID3D11Asynchronous *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Asynchronous, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Asynchronous_SetPrivateDataInterface(ID3D11Asynchronous *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Asynchronous, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static UINT STDMETHODCALLTYPE g_ID3D11Asynchronous_GetDataSize(ID3D11Asynchronous *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Asynchronous, 7};
    LONG status = proxy_call(&packet);
    if (status < 0) { return (UINT)status; }
    return (UINT)packet.ret;
}
static const ID3D11AsynchronousVtbl vtbl_ID3D11Asynchronous = {
    g_ID3D11Asynchronous_QueryInterface,
    g_ID3D11Asynchronous_AddRef,
    g_ID3D11Asynchronous_Release,
    g_ID3D11Asynchronous_GetDevice,
    g_ID3D11Asynchronous_GetPrivateData,
    g_ID3D11Asynchronous_SetPrivateData,
    g_ID3D11Asynchronous_SetPrivateDataInterface,
    g_ID3D11Asynchronous_GetDataSize
};
static HRESULT STDMETHODCALLTYPE g_ID3D11BlendState_QueryInterface(ID3D11BlendState *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11BlendState_AddRef(ID3D11BlendState *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11BlendState_Release(ID3D11BlendState *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11BlendState_GetDevice(ID3D11BlendState *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11BlendState, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11BlendState_GetPrivateData(ID3D11BlendState *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11BlendState_SetPrivateData(ID3D11BlendState *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11BlendState, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11BlendState_SetPrivateDataInterface(ID3D11BlendState *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11BlendState, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static void STDMETHODCALLTYPE g_ID3D11BlendState_GetDesc(ID3D11BlendState *This, D3D11_BLEND_DESC * pDesc) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11BlendState, 7};
    packet.args[0] = guest_address(pDesc);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static const ID3D11BlendStateVtbl vtbl_ID3D11BlendState = {
    g_ID3D11BlendState_QueryInterface,
    g_ID3D11BlendState_AddRef,
    g_ID3D11BlendState_Release,
    g_ID3D11BlendState_GetDevice,
    g_ID3D11BlendState_GetPrivateData,
    g_ID3D11BlendState_SetPrivateData,
    g_ID3D11BlendState_SetPrivateDataInterface,
    g_ID3D11BlendState_GetDesc
};
static HRESULT STDMETHODCALLTYPE g_ID3D11Buffer_QueryInterface(ID3D11Buffer *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11Buffer_AddRef(ID3D11Buffer *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11Buffer_Release(ID3D11Buffer *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11Buffer_GetDevice(ID3D11Buffer *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Buffer, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Buffer_GetPrivateData(ID3D11Buffer *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Buffer_SetPrivateData(ID3D11Buffer *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Buffer, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Buffer_SetPrivateDataInterface(ID3D11Buffer *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Buffer, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static void STDMETHODCALLTYPE g_ID3D11Buffer_GetType(ID3D11Buffer *This, D3D11_RESOURCE_DIMENSION * pResourceDimension) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Buffer, 7};
    packet.args[0] = guest_address(pResourceDimension);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11Buffer_SetEvictionPriority(ID3D11Buffer *This, UINT EvictionPriority) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Buffer, 8};
    packet.args[0] = (uint32_t)EvictionPriority;
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static UINT STDMETHODCALLTYPE g_ID3D11Buffer_GetEvictionPriority(ID3D11Buffer *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Buffer, 9};
    LONG status = proxy_call(&packet);
    if (status < 0) { return (UINT)status; }
    return (UINT)packet.ret;
}
static void STDMETHODCALLTYPE g_ID3D11Buffer_GetDesc(ID3D11Buffer *This, D3D11_BUFFER_DESC * pDesc) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Buffer, 10};
    packet.args[0] = guest_address(pDesc);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static const ID3D11BufferVtbl vtbl_ID3D11Buffer = {
    g_ID3D11Buffer_QueryInterface,
    g_ID3D11Buffer_AddRef,
    g_ID3D11Buffer_Release,
    g_ID3D11Buffer_GetDevice,
    g_ID3D11Buffer_GetPrivateData,
    g_ID3D11Buffer_SetPrivateData,
    g_ID3D11Buffer_SetPrivateDataInterface,
    g_ID3D11Buffer_GetType,
    g_ID3D11Buffer_SetEvictionPriority,
    g_ID3D11Buffer_GetEvictionPriority,
    g_ID3D11Buffer_GetDesc
};
static HRESULT STDMETHODCALLTYPE g_ID3D11ClassInstance_QueryInterface(ID3D11ClassInstance *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11ClassInstance_AddRef(ID3D11ClassInstance *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11ClassInstance_Release(ID3D11ClassInstance *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11ClassInstance_GetDevice(ID3D11ClassInstance *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11ClassInstance, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11ClassInstance_GetPrivateData(ID3D11ClassInstance *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11ClassInstance_SetPrivateData(ID3D11ClassInstance *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11ClassInstance, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11ClassInstance_SetPrivateDataInterface(ID3D11ClassInstance *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11ClassInstance, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static void STDMETHODCALLTYPE g_ID3D11ClassInstance_GetClassLinkage(ID3D11ClassInstance *This, ID3D11ClassLinkage ** ppLinkage) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11ClassInstance, 7};
    struct proxy_output wire_ppLinkage;
    if (!proxy_output_init(&wire_ppLinkage,ppLinkage,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppLinkage.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppLinkage,ppLinkage,safe_array_count(1),SD_COM_IF_ID3D11ClassLinkage)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppLinkage,ppLinkage);
    proxy_output_dispose(&wire_ppLinkage,SD_COM_IF_ID3D11ClassLinkage);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11ClassInstance_GetDesc(ID3D11ClassInstance *This, D3D11_CLASS_INSTANCE_DESC * pDesc) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11ClassInstance, 8};
    packet.args[0] = guest_address(pDesc);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11ClassInstance_GetInstanceName(ID3D11ClassInstance *This, char * pInstanceName, SIZE_T * pBufferLength) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11ClassInstance, 9};
    packet.args[0] = guest_address(pInstanceName);
    packet.args[1] = guest_address(pBufferLength);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11ClassInstance_GetTypeName(ID3D11ClassInstance *This, char * pTypeName, SIZE_T * pBufferLength) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11ClassInstance, 10};
    packet.args[0] = guest_address(pTypeName);
    packet.args[1] = guest_address(pBufferLength);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static const ID3D11ClassInstanceVtbl vtbl_ID3D11ClassInstance = {
    g_ID3D11ClassInstance_QueryInterface,
    g_ID3D11ClassInstance_AddRef,
    g_ID3D11ClassInstance_Release,
    g_ID3D11ClassInstance_GetDevice,
    g_ID3D11ClassInstance_GetPrivateData,
    g_ID3D11ClassInstance_SetPrivateData,
    g_ID3D11ClassInstance_SetPrivateDataInterface,
    g_ID3D11ClassInstance_GetClassLinkage,
    g_ID3D11ClassInstance_GetDesc,
    g_ID3D11ClassInstance_GetInstanceName,
    g_ID3D11ClassInstance_GetTypeName
};
static HRESULT STDMETHODCALLTYPE g_ID3D11ClassLinkage_QueryInterface(ID3D11ClassLinkage *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11ClassLinkage_AddRef(ID3D11ClassLinkage *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11ClassLinkage_Release(ID3D11ClassLinkage *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11ClassLinkage_GetDevice(ID3D11ClassLinkage *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11ClassLinkage, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11ClassLinkage_GetPrivateData(ID3D11ClassLinkage *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11ClassLinkage_SetPrivateData(ID3D11ClassLinkage *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11ClassLinkage, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11ClassLinkage_SetPrivateDataInterface(ID3D11ClassLinkage *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11ClassLinkage, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11ClassLinkage_GetClassInstance(ID3D11ClassLinkage *This, const char * pClassInstanceName, UINT InstanceIndex, ID3D11ClassInstance ** ppInstance) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11ClassLinkage, 7};
    packet.args[0] = guest_address(pClassInstanceName);
    packet.args[1] = (uint32_t)InstanceIndex;
    struct proxy_output wire_ppInstance;
    if (!proxy_output_init(&wire_ppInstance,ppInstance,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[2] = guest_address(wire_ppInstance.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppInstance,ppInstance,safe_array_count(1),SD_COM_IF_ID3D11ClassInstance)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppInstance,ppInstance);
    proxy_output_dispose(&wire_ppInstance,SD_COM_IF_ID3D11ClassInstance);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11ClassLinkage_CreateClassInstance(ID3D11ClassLinkage *This, const char * pClassTypeName, UINT ConstantBufferOffset, UINT ConstantVectorOffset, UINT TextureOffset, UINT SamplerOffset, ID3D11ClassInstance ** ppInstance) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11ClassLinkage, 8};
    packet.args[0] = guest_address(pClassTypeName);
    packet.args[1] = (uint32_t)ConstantBufferOffset;
    packet.args[2] = (uint32_t)ConstantVectorOffset;
    packet.args[3] = (uint32_t)TextureOffset;
    packet.args[4] = (uint32_t)SamplerOffset;
    struct proxy_output wire_ppInstance;
    if (!proxy_output_init(&wire_ppInstance,ppInstance,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[5] = guest_address(wire_ppInstance.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppInstance,ppInstance,safe_array_count(1),SD_COM_IF_ID3D11ClassInstance)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppInstance,ppInstance);
    proxy_output_dispose(&wire_ppInstance,SD_COM_IF_ID3D11ClassInstance);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static const ID3D11ClassLinkageVtbl vtbl_ID3D11ClassLinkage = {
    g_ID3D11ClassLinkage_QueryInterface,
    g_ID3D11ClassLinkage_AddRef,
    g_ID3D11ClassLinkage_Release,
    g_ID3D11ClassLinkage_GetDevice,
    g_ID3D11ClassLinkage_GetPrivateData,
    g_ID3D11ClassLinkage_SetPrivateData,
    g_ID3D11ClassLinkage_SetPrivateDataInterface,
    g_ID3D11ClassLinkage_GetClassInstance,
    g_ID3D11ClassLinkage_CreateClassInstance
};
static HRESULT STDMETHODCALLTYPE g_ID3D11CommandList_QueryInterface(ID3D11CommandList *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11CommandList_AddRef(ID3D11CommandList *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11CommandList_Release(ID3D11CommandList *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11CommandList_GetDevice(ID3D11CommandList *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11CommandList, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11CommandList_GetPrivateData(ID3D11CommandList *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11CommandList_SetPrivateData(ID3D11CommandList *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11CommandList, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11CommandList_SetPrivateDataInterface(ID3D11CommandList *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11CommandList, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static UINT STDMETHODCALLTYPE g_ID3D11CommandList_GetContextFlags(ID3D11CommandList *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11CommandList, 7};
    LONG status = proxy_call(&packet);
    if (status < 0) { return (UINT)status; }
    return (UINT)packet.ret;
}
static const ID3D11CommandListVtbl vtbl_ID3D11CommandList = {
    g_ID3D11CommandList_QueryInterface,
    g_ID3D11CommandList_AddRef,
    g_ID3D11CommandList_Release,
    g_ID3D11CommandList_GetDevice,
    g_ID3D11CommandList_GetPrivateData,
    g_ID3D11CommandList_SetPrivateData,
    g_ID3D11CommandList_SetPrivateDataInterface,
    g_ID3D11CommandList_GetContextFlags
};
static HRESULT STDMETHODCALLTYPE g_ID3D11ComputeShader_QueryInterface(ID3D11ComputeShader *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11ComputeShader_AddRef(ID3D11ComputeShader *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11ComputeShader_Release(ID3D11ComputeShader *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11ComputeShader_GetDevice(ID3D11ComputeShader *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11ComputeShader, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11ComputeShader_GetPrivateData(ID3D11ComputeShader *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11ComputeShader_SetPrivateData(ID3D11ComputeShader *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11ComputeShader, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11ComputeShader_SetPrivateDataInterface(ID3D11ComputeShader *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11ComputeShader, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static const ID3D11ComputeShaderVtbl vtbl_ID3D11ComputeShader = {
    g_ID3D11ComputeShader_QueryInterface,
    g_ID3D11ComputeShader_AddRef,
    g_ID3D11ComputeShader_Release,
    g_ID3D11ComputeShader_GetDevice,
    g_ID3D11ComputeShader_GetPrivateData,
    g_ID3D11ComputeShader_SetPrivateData,
    g_ID3D11ComputeShader_SetPrivateDataInterface
};
static HRESULT STDMETHODCALLTYPE g_ID3D11Counter_QueryInterface(ID3D11Counter *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11Counter_AddRef(ID3D11Counter *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11Counter_Release(ID3D11Counter *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11Counter_GetDevice(ID3D11Counter *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Counter, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Counter_GetPrivateData(ID3D11Counter *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Counter_SetPrivateData(ID3D11Counter *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Counter, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Counter_SetPrivateDataInterface(ID3D11Counter *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Counter, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static UINT STDMETHODCALLTYPE g_ID3D11Counter_GetDataSize(ID3D11Counter *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Counter, 7};
    LONG status = proxy_call(&packet);
    if (status < 0) { return (UINT)status; }
    return (UINT)packet.ret;
}
static void STDMETHODCALLTYPE g_ID3D11Counter_GetDesc(ID3D11Counter *This, D3D11_COUNTER_DESC * pDesc) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Counter, 8};
    packet.args[0] = guest_address(pDesc);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static const ID3D11CounterVtbl vtbl_ID3D11Counter = {
    g_ID3D11Counter_QueryInterface,
    g_ID3D11Counter_AddRef,
    g_ID3D11Counter_Release,
    g_ID3D11Counter_GetDevice,
    g_ID3D11Counter_GetPrivateData,
    g_ID3D11Counter_SetPrivateData,
    g_ID3D11Counter_SetPrivateDataInterface,
    g_ID3D11Counter_GetDataSize,
    g_ID3D11Counter_GetDesc
};
static HRESULT STDMETHODCALLTYPE g_ID3D11DepthStencilState_QueryInterface(ID3D11DepthStencilState *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11DepthStencilState_AddRef(ID3D11DepthStencilState *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11DepthStencilState_Release(ID3D11DepthStencilState *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11DepthStencilState_GetDevice(ID3D11DepthStencilState *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DepthStencilState, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11DepthStencilState_GetPrivateData(ID3D11DepthStencilState *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11DepthStencilState_SetPrivateData(ID3D11DepthStencilState *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DepthStencilState, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11DepthStencilState_SetPrivateDataInterface(ID3D11DepthStencilState *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DepthStencilState, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static void STDMETHODCALLTYPE g_ID3D11DepthStencilState_GetDesc(ID3D11DepthStencilState *This, D3D11_DEPTH_STENCIL_DESC * pDesc) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DepthStencilState, 7};
    packet.args[0] = guest_address(pDesc);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static const ID3D11DepthStencilStateVtbl vtbl_ID3D11DepthStencilState = {
    g_ID3D11DepthStencilState_QueryInterface,
    g_ID3D11DepthStencilState_AddRef,
    g_ID3D11DepthStencilState_Release,
    g_ID3D11DepthStencilState_GetDevice,
    g_ID3D11DepthStencilState_GetPrivateData,
    g_ID3D11DepthStencilState_SetPrivateData,
    g_ID3D11DepthStencilState_SetPrivateDataInterface,
    g_ID3D11DepthStencilState_GetDesc
};
static HRESULT STDMETHODCALLTYPE g_ID3D11DepthStencilView_QueryInterface(ID3D11DepthStencilView *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11DepthStencilView_AddRef(ID3D11DepthStencilView *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11DepthStencilView_Release(ID3D11DepthStencilView *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11DepthStencilView_GetDevice(ID3D11DepthStencilView *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DepthStencilView, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11DepthStencilView_GetPrivateData(ID3D11DepthStencilView *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11DepthStencilView_SetPrivateData(ID3D11DepthStencilView *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DepthStencilView, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11DepthStencilView_SetPrivateDataInterface(ID3D11DepthStencilView *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DepthStencilView, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static void STDMETHODCALLTYPE g_ID3D11DepthStencilView_GetResource(ID3D11DepthStencilView *This, ID3D11Resource ** ppResource) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DepthStencilView, 7};
    struct proxy_output wire_ppResource;
    if (!proxy_output_init(&wire_ppResource,ppResource,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppResource.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppResource,ppResource,safe_array_count(1),SD_COM_IF_ID3D11Resource)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppResource,ppResource);
    proxy_output_dispose(&wire_ppResource,SD_COM_IF_ID3D11Resource);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DepthStencilView_GetDesc(ID3D11DepthStencilView *This, D3D11_DEPTH_STENCIL_VIEW_DESC * pDesc) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DepthStencilView, 8};
    packet.args[0] = guest_address(pDesc);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static const ID3D11DepthStencilViewVtbl vtbl_ID3D11DepthStencilView = {
    g_ID3D11DepthStencilView_QueryInterface,
    g_ID3D11DepthStencilView_AddRef,
    g_ID3D11DepthStencilView_Release,
    g_ID3D11DepthStencilView_GetDevice,
    g_ID3D11DepthStencilView_GetPrivateData,
    g_ID3D11DepthStencilView_SetPrivateData,
    g_ID3D11DepthStencilView_SetPrivateDataInterface,
    g_ID3D11DepthStencilView_GetResource,
    g_ID3D11DepthStencilView_GetDesc
};
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_QueryInterface(ID3D11Device *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11Device_AddRef(ID3D11Device *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11Device_Release(ID3D11Device *This) {
    return proxy_release(This);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CreateBuffer(ID3D11Device *This, const D3D11_BUFFER_DESC * pDesc, const D3D11_SUBRESOURCE_DATA * pInitialData, ID3D11Buffer ** ppBuffer) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 3};
    packet.args[0] = guest_address(pDesc);
    packet.args[1] = guest_address(pInitialData);
    struct proxy_output wire_ppBuffer;
    if (!proxy_output_init(&wire_ppBuffer,ppBuffer,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[2] = guest_address(wire_ppBuffer.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppBuffer,ppBuffer,safe_array_count(1),SD_COM_IF_ID3D11Buffer)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppBuffer,ppBuffer);
    proxy_output_dispose(&wire_ppBuffer,SD_COM_IF_ID3D11Buffer);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CreateTexture1D(ID3D11Device *This, const D3D11_TEXTURE1D_DESC * pDesc, const D3D11_SUBRESOURCE_DATA * pInitialData, ID3D11Texture1D ** ppTexture1D) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 4};
    packet.args[0] = guest_address(pDesc);
    packet.args[1] = guest_address(pInitialData);
    struct proxy_output wire_ppTexture1D;
    if (!proxy_output_init(&wire_ppTexture1D,ppTexture1D,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[2] = guest_address(wire_ppTexture1D.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppTexture1D,ppTexture1D,safe_array_count(1),SD_COM_IF_ID3D11Texture1D)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppTexture1D,ppTexture1D);
    proxy_output_dispose(&wire_ppTexture1D,SD_COM_IF_ID3D11Texture1D);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CreateTexture2D(ID3D11Device *This, const D3D11_TEXTURE2D_DESC * pDesc, const D3D11_SUBRESOURCE_DATA * pInitialData, ID3D11Texture2D ** ppTexture2D) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 5};
    packet.args[0] = guest_address(pDesc);
    packet.args[1] = guest_address(pInitialData);
    struct proxy_output wire_ppTexture2D;
    if (!proxy_output_init(&wire_ppTexture2D,ppTexture2D,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[2] = guest_address(wire_ppTexture2D.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppTexture2D,ppTexture2D,safe_array_count(1),SD_COM_IF_ID3D11Texture2D)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppTexture2D,ppTexture2D);
    proxy_output_dispose(&wire_ppTexture2D,SD_COM_IF_ID3D11Texture2D);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CreateTexture3D(ID3D11Device *This, const D3D11_TEXTURE3D_DESC * pDesc, const D3D11_SUBRESOURCE_DATA * pInitialData, ID3D11Texture3D ** ppTexture3D) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 6};
    packet.args[0] = guest_address(pDesc);
    packet.args[1] = guest_address(pInitialData);
    struct proxy_output wire_ppTexture3D;
    if (!proxy_output_init(&wire_ppTexture3D,ppTexture3D,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[2] = guest_address(wire_ppTexture3D.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppTexture3D,ppTexture3D,safe_array_count(1),SD_COM_IF_ID3D11Texture3D)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppTexture3D,ppTexture3D);
    proxy_output_dispose(&wire_ppTexture3D,SD_COM_IF_ID3D11Texture3D);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CreateShaderResourceView(ID3D11Device *This, ID3D11Resource * pResource, const D3D11_SHADER_RESOURCE_VIEW_DESC * pDesc, ID3D11ShaderResourceView ** ppSRView) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 7};
    packet.args[0] = proxy_token(pResource);
    packet.args[1] = guest_address(pDesc);
    struct proxy_output wire_ppSRView;
    if (!proxy_output_init(&wire_ppSRView,ppSRView,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[2] = guest_address(wire_ppSRView.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppSRView,ppSRView,safe_array_count(1),SD_COM_IF_ID3D11ShaderResourceView)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppSRView,ppSRView);
    proxy_output_dispose(&wire_ppSRView,SD_COM_IF_ID3D11ShaderResourceView);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CreateUnorderedAccessView(ID3D11Device *This, ID3D11Resource * pResource, const D3D11_UNORDERED_ACCESS_VIEW_DESC * pDesc, ID3D11UnorderedAccessView ** ppUAView) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 8};
    packet.args[0] = proxy_token(pResource);
    packet.args[1] = guest_address(pDesc);
    struct proxy_output wire_ppUAView;
    if (!proxy_output_init(&wire_ppUAView,ppUAView,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[2] = guest_address(wire_ppUAView.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppUAView,ppUAView,safe_array_count(1),SD_COM_IF_ID3D11UnorderedAccessView)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppUAView,ppUAView);
    proxy_output_dispose(&wire_ppUAView,SD_COM_IF_ID3D11UnorderedAccessView);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CreateRenderTargetView(ID3D11Device *This, ID3D11Resource * pResource, const D3D11_RENDER_TARGET_VIEW_DESC * pDesc, ID3D11RenderTargetView ** ppRTView) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 9};
    packet.args[0] = proxy_token(pResource);
    packet.args[1] = guest_address(pDesc);
    struct proxy_output wire_ppRTView;
    if (!proxy_output_init(&wire_ppRTView,ppRTView,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[2] = guest_address(wire_ppRTView.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppRTView,ppRTView,safe_array_count(1),SD_COM_IF_ID3D11RenderTargetView)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppRTView,ppRTView);
    proxy_output_dispose(&wire_ppRTView,SD_COM_IF_ID3D11RenderTargetView);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CreateDepthStencilView(ID3D11Device *This, ID3D11Resource * pResource, const D3D11_DEPTH_STENCIL_VIEW_DESC * pDesc, ID3D11DepthStencilView ** ppDepthStencilView) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 10};
    packet.args[0] = proxy_token(pResource);
    packet.args[1] = guest_address(pDesc);
    struct proxy_output wire_ppDepthStencilView;
    if (!proxy_output_init(&wire_ppDepthStencilView,ppDepthStencilView,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[2] = guest_address(wire_ppDepthStencilView.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppDepthStencilView,ppDepthStencilView,safe_array_count(1),SD_COM_IF_ID3D11DepthStencilView)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppDepthStencilView,ppDepthStencilView);
    proxy_output_dispose(&wire_ppDepthStencilView,SD_COM_IF_ID3D11DepthStencilView);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CreateInputLayout(ID3D11Device *This, const D3D11_INPUT_ELEMENT_DESC * pInputElementDescs, UINT NumElements, const void * pShaderBytecodeWithInputSignature, SIZE_T BytecodeLength, ID3D11InputLayout ** ppInputLayout) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 11};
    packet.args[0] = guest_address(pInputElementDescs);
    packet.args[1] = (uint32_t)NumElements;
    packet.args[2] = guest_address(pShaderBytecodeWithInputSignature);
    packet.args[3] = (uint32_t)BytecodeLength;
    struct proxy_output wire_ppInputLayout;
    if (!proxy_output_init(&wire_ppInputLayout,ppInputLayout,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[4] = guest_address(wire_ppInputLayout.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppInputLayout,ppInputLayout,safe_array_count(1),SD_COM_IF_ID3D11InputLayout)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppInputLayout,ppInputLayout);
    proxy_output_dispose(&wire_ppInputLayout,SD_COM_IF_ID3D11InputLayout);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CreateVertexShader(ID3D11Device *This, const void * pShaderBytecode, SIZE_T BytecodeLength, ID3D11ClassLinkage * pClassLinkage, ID3D11VertexShader ** ppVertexShader) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 12};
    packet.args[0] = guest_address(pShaderBytecode);
    packet.args[1] = (uint32_t)BytecodeLength;
    packet.args[2] = proxy_token(pClassLinkage);
    struct proxy_output wire_ppVertexShader;
    if (!proxy_output_init(&wire_ppVertexShader,ppVertexShader,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[3] = guest_address(wire_ppVertexShader.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppVertexShader,ppVertexShader,safe_array_count(1),SD_COM_IF_ID3D11VertexShader)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppVertexShader,ppVertexShader);
    proxy_output_dispose(&wire_ppVertexShader,SD_COM_IF_ID3D11VertexShader);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CreateGeometryShader(ID3D11Device *This, const void * pShaderBytecode, SIZE_T BytecodeLength, ID3D11ClassLinkage * pClassLinkage, ID3D11GeometryShader ** ppGeometryShader) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 13};
    packet.args[0] = guest_address(pShaderBytecode);
    packet.args[1] = (uint32_t)BytecodeLength;
    packet.args[2] = proxy_token(pClassLinkage);
    struct proxy_output wire_ppGeometryShader;
    if (!proxy_output_init(&wire_ppGeometryShader,ppGeometryShader,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[3] = guest_address(wire_ppGeometryShader.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppGeometryShader,ppGeometryShader,safe_array_count(1),SD_COM_IF_ID3D11GeometryShader)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppGeometryShader,ppGeometryShader);
    proxy_output_dispose(&wire_ppGeometryShader,SD_COM_IF_ID3D11GeometryShader);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CreateGeometryShaderWithStreamOutput(ID3D11Device *This, const void * pShaderBytecode, SIZE_T BytecodeLength, const D3D11_SO_DECLARATION_ENTRY * pSODeclaration, UINT NumEntries, const UINT * pBufferStrides, UINT NumStrides, UINT RasterizedStream, ID3D11ClassLinkage * pClassLinkage, ID3D11GeometryShader ** ppGeometryShader) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 14};
    packet.args[0] = guest_address(pShaderBytecode);
    packet.args[1] = (uint32_t)BytecodeLength;
    packet.args[2] = guest_address(pSODeclaration);
    packet.args[3] = (uint32_t)NumEntries;
    packet.args[4] = guest_address(pBufferStrides);
    packet.args[5] = (uint32_t)NumStrides;
    packet.args[6] = (uint32_t)RasterizedStream;
    packet.args[7] = proxy_token(pClassLinkage);
    struct proxy_output wire_ppGeometryShader;
    if (!proxy_output_init(&wire_ppGeometryShader,ppGeometryShader,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[8] = guest_address(wire_ppGeometryShader.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppGeometryShader,ppGeometryShader,safe_array_count(1),SD_COM_IF_ID3D11GeometryShader)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppGeometryShader,ppGeometryShader);
    proxy_output_dispose(&wire_ppGeometryShader,SD_COM_IF_ID3D11GeometryShader);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CreatePixelShader(ID3D11Device *This, const void * pShaderBytecode, SIZE_T BytecodeLength, ID3D11ClassLinkage * pClassLinkage, ID3D11PixelShader ** ppPixelShader) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 15};
    packet.args[0] = guest_address(pShaderBytecode);
    packet.args[1] = (uint32_t)BytecodeLength;
    packet.args[2] = proxy_token(pClassLinkage);
    struct proxy_output wire_ppPixelShader;
    if (!proxy_output_init(&wire_ppPixelShader,ppPixelShader,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[3] = guest_address(wire_ppPixelShader.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppPixelShader,ppPixelShader,safe_array_count(1),SD_COM_IF_ID3D11PixelShader)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppPixelShader,ppPixelShader);
    proxy_output_dispose(&wire_ppPixelShader,SD_COM_IF_ID3D11PixelShader);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CreateHullShader(ID3D11Device *This, const void * pShaderBytecode, SIZE_T BytecodeLength, ID3D11ClassLinkage * pClassLinkage, ID3D11HullShader ** ppHullShader) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 16};
    packet.args[0] = guest_address(pShaderBytecode);
    packet.args[1] = (uint32_t)BytecodeLength;
    packet.args[2] = proxy_token(pClassLinkage);
    struct proxy_output wire_ppHullShader;
    if (!proxy_output_init(&wire_ppHullShader,ppHullShader,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[3] = guest_address(wire_ppHullShader.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppHullShader,ppHullShader,safe_array_count(1),SD_COM_IF_ID3D11HullShader)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppHullShader,ppHullShader);
    proxy_output_dispose(&wire_ppHullShader,SD_COM_IF_ID3D11HullShader);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CreateDomainShader(ID3D11Device *This, const void * pShaderBytecode, SIZE_T BytecodeLength, ID3D11ClassLinkage * pClassLinkage, ID3D11DomainShader ** ppDomainShader) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 17};
    packet.args[0] = guest_address(pShaderBytecode);
    packet.args[1] = (uint32_t)BytecodeLength;
    packet.args[2] = proxy_token(pClassLinkage);
    struct proxy_output wire_ppDomainShader;
    if (!proxy_output_init(&wire_ppDomainShader,ppDomainShader,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[3] = guest_address(wire_ppDomainShader.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppDomainShader,ppDomainShader,safe_array_count(1),SD_COM_IF_ID3D11DomainShader)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppDomainShader,ppDomainShader);
    proxy_output_dispose(&wire_ppDomainShader,SD_COM_IF_ID3D11DomainShader);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CreateComputeShader(ID3D11Device *This, const void * pShaderBytecode, SIZE_T BytecodeLength, ID3D11ClassLinkage * pClassLinkage, ID3D11ComputeShader ** ppComputeShader) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 18};
    packet.args[0] = guest_address(pShaderBytecode);
    packet.args[1] = (uint32_t)BytecodeLength;
    packet.args[2] = proxy_token(pClassLinkage);
    struct proxy_output wire_ppComputeShader;
    if (!proxy_output_init(&wire_ppComputeShader,ppComputeShader,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[3] = guest_address(wire_ppComputeShader.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppComputeShader,ppComputeShader,safe_array_count(1),SD_COM_IF_ID3D11ComputeShader)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppComputeShader,ppComputeShader);
    proxy_output_dispose(&wire_ppComputeShader,SD_COM_IF_ID3D11ComputeShader);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CreateClassLinkage(ID3D11Device *This, ID3D11ClassLinkage ** ppLinkage) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 19};
    struct proxy_output wire_ppLinkage;
    if (!proxy_output_init(&wire_ppLinkage,ppLinkage,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[0] = guest_address(wire_ppLinkage.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppLinkage,ppLinkage,safe_array_count(1),SD_COM_IF_ID3D11ClassLinkage)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppLinkage,ppLinkage);
    proxy_output_dispose(&wire_ppLinkage,SD_COM_IF_ID3D11ClassLinkage);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CreateBlendState(ID3D11Device *This, const D3D11_BLEND_DESC * pBlendStateDesc, ID3D11BlendState ** ppBlendState) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 20};
    packet.args[0] = guest_address(pBlendStateDesc);
    struct proxy_output wire_ppBlendState;
    if (!proxy_output_init(&wire_ppBlendState,ppBlendState,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_ppBlendState.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppBlendState,ppBlendState,safe_array_count(1),SD_COM_IF_ID3D11BlendState)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppBlendState,ppBlendState);
    proxy_output_dispose(&wire_ppBlendState,SD_COM_IF_ID3D11BlendState);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CreateDepthStencilState(ID3D11Device *This, const D3D11_DEPTH_STENCIL_DESC * pDepthStencilDesc, ID3D11DepthStencilState ** ppDepthStencilState) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 21};
    packet.args[0] = guest_address(pDepthStencilDesc);
    struct proxy_output wire_ppDepthStencilState;
    if (!proxy_output_init(&wire_ppDepthStencilState,ppDepthStencilState,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_ppDepthStencilState.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppDepthStencilState,ppDepthStencilState,safe_array_count(1),SD_COM_IF_ID3D11DepthStencilState)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppDepthStencilState,ppDepthStencilState);
    proxy_output_dispose(&wire_ppDepthStencilState,SD_COM_IF_ID3D11DepthStencilState);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CreateRasterizerState(ID3D11Device *This, const D3D11_RASTERIZER_DESC * pRasterizerDesc, ID3D11RasterizerState ** ppRasterizerState) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 22};
    packet.args[0] = guest_address(pRasterizerDesc);
    struct proxy_output wire_ppRasterizerState;
    if (!proxy_output_init(&wire_ppRasterizerState,ppRasterizerState,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_ppRasterizerState.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppRasterizerState,ppRasterizerState,safe_array_count(1),SD_COM_IF_ID3D11RasterizerState)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppRasterizerState,ppRasterizerState);
    proxy_output_dispose(&wire_ppRasterizerState,SD_COM_IF_ID3D11RasterizerState);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CreateSamplerState(ID3D11Device *This, const D3D11_SAMPLER_DESC * pSamplerDesc, ID3D11SamplerState ** ppSamplerState) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 23};
    packet.args[0] = guest_address(pSamplerDesc);
    struct proxy_output wire_ppSamplerState;
    if (!proxy_output_init(&wire_ppSamplerState,ppSamplerState,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_ppSamplerState.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppSamplerState,ppSamplerState,safe_array_count(1),SD_COM_IF_ID3D11SamplerState)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppSamplerState,ppSamplerState);
    proxy_output_dispose(&wire_ppSamplerState,SD_COM_IF_ID3D11SamplerState);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CreateQuery(ID3D11Device *This, const D3D11_QUERY_DESC * pQueryDesc, ID3D11Query ** ppQuery) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 24};
    packet.args[0] = guest_address(pQueryDesc);
    struct proxy_output wire_ppQuery;
    if (!proxy_output_init(&wire_ppQuery,ppQuery,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_ppQuery.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppQuery,ppQuery,safe_array_count(1),SD_COM_IF_ID3D11Query)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppQuery,ppQuery);
    proxy_output_dispose(&wire_ppQuery,SD_COM_IF_ID3D11Query);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CreatePredicate(ID3D11Device *This, const D3D11_QUERY_DESC * pPredicateDesc, ID3D11Predicate ** ppPredicate) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 25};
    packet.args[0] = guest_address(pPredicateDesc);
    struct proxy_output wire_ppPredicate;
    if (!proxy_output_init(&wire_ppPredicate,ppPredicate,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_ppPredicate.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppPredicate,ppPredicate,safe_array_count(1),SD_COM_IF_ID3D11Predicate)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppPredicate,ppPredicate);
    proxy_output_dispose(&wire_ppPredicate,SD_COM_IF_ID3D11Predicate);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CreateCounter(ID3D11Device *This, const D3D11_COUNTER_DESC * pCounterDesc, ID3D11Counter ** ppCounter) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 26};
    packet.args[0] = guest_address(pCounterDesc);
    struct proxy_output wire_ppCounter;
    if (!proxy_output_init(&wire_ppCounter,ppCounter,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_ppCounter.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppCounter,ppCounter,safe_array_count(1),SD_COM_IF_ID3D11Counter)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppCounter,ppCounter);
    proxy_output_dispose(&wire_ppCounter,SD_COM_IF_ID3D11Counter);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CreateDeferredContext(ID3D11Device *This, UINT ContextFlags, ID3D11DeviceContext ** ppDeferredContext) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 27};
    packet.args[0] = (uint32_t)ContextFlags;
    struct proxy_output wire_ppDeferredContext;
    if (!proxy_output_init(&wire_ppDeferredContext,ppDeferredContext,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_ppDeferredContext.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppDeferredContext,ppDeferredContext,safe_array_count(1),SD_COM_IF_ID3D11DeviceContext)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppDeferredContext,ppDeferredContext);
    proxy_output_dispose(&wire_ppDeferredContext,SD_COM_IF_ID3D11DeviceContext);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_OpenSharedResource(ID3D11Device *This, HANDLE hResource, REFIID ReturnedInterface, void ** ppResource) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 28};
    packet.args[0] = guest_address(hResource);
    packet.args[1] = guest_address(ReturnedInterface);
    struct proxy_output wire_ppResource;
    if (!proxy_output_init(&wire_ppResource,ppResource,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[2] = guest_address(wire_ppResource.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppResource,ppResource,safe_array_count(1),proxy_iid(ReturnedInterface))) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppResource,ppResource);
    proxy_output_dispose(&wire_ppResource,proxy_iid(ReturnedInterface));
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CheckFormatSupport(ID3D11Device *This, DXGI_FORMAT Format, UINT * pFormatSupport) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 29};
    packet.args[0] = (uint32_t)Format;
    packet.args[1] = guest_address(pFormatSupport);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CheckMultisampleQualityLevels(ID3D11Device *This, DXGI_FORMAT Format, UINT SampleCount, UINT * pNumQualityLevels) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 30};
    packet.args[0] = (uint32_t)Format;
    packet.args[1] = (uint32_t)SampleCount;
    packet.args[2] = guest_address(pNumQualityLevels);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static void STDMETHODCALLTYPE g_ID3D11Device_CheckCounterInfo(ID3D11Device *This, D3D11_COUNTER_INFO * pCounterInfo) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 31};
    packet.args[0] = guest_address(pCounterInfo);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CheckCounter(ID3D11Device *This, const D3D11_COUNTER_DESC * pDesc, D3D11_COUNTER_TYPE * pType, UINT * pActiveCounters, char * szName, UINT * pNameLength, char * szUnits, UINT * pUnitsLength, char * szDescription, UINT * pDescriptionLength) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 32};
    packet.args[0] = guest_address(pDesc);
    packet.args[1] = guest_address(pType);
    packet.args[2] = guest_address(pActiveCounters);
    packet.args[3] = guest_address(szName);
    packet.args[4] = guest_address(pNameLength);
    packet.args[5] = guest_address(szUnits);
    packet.args[6] = guest_address(pUnitsLength);
    packet.args[7] = guest_address(szDescription);
    packet.args[8] = guest_address(pDescriptionLength);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_CheckFeatureSupport(ID3D11Device *This, D3D11_FEATURE Feature, void * pFeatureSupportData, UINT FeatureSupportDataSize) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 33};
    packet.args[0] = (uint32_t)Feature;
    packet.args[1] = guest_address(pFeatureSupportData);
    packet.args[2] = (uint32_t)FeatureSupportDataSize;
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_GetPrivateData(ID3D11Device *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 34, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_SetPrivateData(ID3D11Device *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 35};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_SetPrivateDataInterface(ID3D11Device *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 36};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static D3D_FEATURE_LEVEL STDMETHODCALLTYPE g_ID3D11Device_GetFeatureLevel(ID3D11Device *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 37};
    LONG status = proxy_call(&packet);
    if (status < 0) { return (D3D_FEATURE_LEVEL)status; }
    return (D3D_FEATURE_LEVEL)packet.ret;
}
static UINT STDMETHODCALLTYPE g_ID3D11Device_GetCreationFlags(ID3D11Device *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 38};
    LONG status = proxy_call(&packet);
    if (status < 0) { return (UINT)status; }
    return (UINT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_GetDeviceRemovedReason(ID3D11Device *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 39};
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static void STDMETHODCALLTYPE g_ID3D11Device_GetImmediateContext(ID3D11Device *This, ID3D11DeviceContext ** ppImmediateContext) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 40};
    struct proxy_output wire_ppImmediateContext;
    if (!proxy_output_init(&wire_ppImmediateContext,ppImmediateContext,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppImmediateContext.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppImmediateContext,ppImmediateContext,safe_array_count(1),SD_COM_IF_ID3D11DeviceContext)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppImmediateContext,ppImmediateContext);
    proxy_output_dispose(&wire_ppImmediateContext,SD_COM_IF_ID3D11DeviceContext);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Device_SetExceptionMode(ID3D11Device *This, UINT RaiseFlags) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 41};
    packet.args[0] = (uint32_t)RaiseFlags;
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static UINT STDMETHODCALLTYPE g_ID3D11Device_GetExceptionMode(ID3D11Device *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Device, 42};
    LONG status = proxy_call(&packet);
    if (status < 0) { return (UINT)status; }
    return (UINT)packet.ret;
}
static const ID3D11DeviceVtbl vtbl_ID3D11Device = {
    g_ID3D11Device_QueryInterface,
    g_ID3D11Device_AddRef,
    g_ID3D11Device_Release,
    g_ID3D11Device_CreateBuffer,
    g_ID3D11Device_CreateTexture1D,
    g_ID3D11Device_CreateTexture2D,
    g_ID3D11Device_CreateTexture3D,
    g_ID3D11Device_CreateShaderResourceView,
    g_ID3D11Device_CreateUnorderedAccessView,
    g_ID3D11Device_CreateRenderTargetView,
    g_ID3D11Device_CreateDepthStencilView,
    g_ID3D11Device_CreateInputLayout,
    g_ID3D11Device_CreateVertexShader,
    g_ID3D11Device_CreateGeometryShader,
    g_ID3D11Device_CreateGeometryShaderWithStreamOutput,
    g_ID3D11Device_CreatePixelShader,
    g_ID3D11Device_CreateHullShader,
    g_ID3D11Device_CreateDomainShader,
    g_ID3D11Device_CreateComputeShader,
    g_ID3D11Device_CreateClassLinkage,
    g_ID3D11Device_CreateBlendState,
    g_ID3D11Device_CreateDepthStencilState,
    g_ID3D11Device_CreateRasterizerState,
    g_ID3D11Device_CreateSamplerState,
    g_ID3D11Device_CreateQuery,
    g_ID3D11Device_CreatePredicate,
    g_ID3D11Device_CreateCounter,
    g_ID3D11Device_CreateDeferredContext,
    g_ID3D11Device_OpenSharedResource,
    g_ID3D11Device_CheckFormatSupport,
    g_ID3D11Device_CheckMultisampleQualityLevels,
    g_ID3D11Device_CheckCounterInfo,
    g_ID3D11Device_CheckCounter,
    g_ID3D11Device_CheckFeatureSupport,
    g_ID3D11Device_GetPrivateData,
    g_ID3D11Device_SetPrivateData,
    g_ID3D11Device_SetPrivateDataInterface,
    g_ID3D11Device_GetFeatureLevel,
    g_ID3D11Device_GetCreationFlags,
    g_ID3D11Device_GetDeviceRemovedReason,
    g_ID3D11Device_GetImmediateContext,
    g_ID3D11Device_SetExceptionMode,
    g_ID3D11Device_GetExceptionMode
};
static HRESULT STDMETHODCALLTYPE g_ID3D11DeviceChild_QueryInterface(ID3D11DeviceChild *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11DeviceChild_AddRef(ID3D11DeviceChild *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11DeviceChild_Release(ID3D11DeviceChild *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceChild_GetDevice(ID3D11DeviceChild *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceChild, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11DeviceChild_GetPrivateData(ID3D11DeviceChild *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11DeviceChild_SetPrivateData(ID3D11DeviceChild *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceChild, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11DeviceChild_SetPrivateDataInterface(ID3D11DeviceChild *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceChild, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static const ID3D11DeviceChildVtbl vtbl_ID3D11DeviceChild = {
    g_ID3D11DeviceChild_QueryInterface,
    g_ID3D11DeviceChild_AddRef,
    g_ID3D11DeviceChild_Release,
    g_ID3D11DeviceChild_GetDevice,
    g_ID3D11DeviceChild_GetPrivateData,
    g_ID3D11DeviceChild_SetPrivateData,
    g_ID3D11DeviceChild_SetPrivateDataInterface
};
static HRESULT STDMETHODCALLTYPE g_ID3D11DeviceContext_QueryInterface(ID3D11DeviceContext *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11DeviceContext_AddRef(ID3D11DeviceContext *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11DeviceContext_Release(ID3D11DeviceContext *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_GetDevice(ID3D11DeviceContext *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11DeviceContext_GetPrivateData(ID3D11DeviceContext *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11DeviceContext_SetPrivateData(ID3D11DeviceContext *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11DeviceContext_SetPrivateDataInterface(ID3D11DeviceContext *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_VSSetConstantBuffers(ID3D11DeviceContext *This, UINT StartSlot, UINT NumBuffers, ID3D11Buffer *const * ppConstantBuffers) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 7};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumBuffers;
    UINT count_ppConstantBuffers = safe_array_count(NumBuffers);
    uint32_t stack_ppConstantBuffers[128];
    uint32_t *tokens_ppConstantBuffers = ppConstantBuffers && count_ppConstantBuffers ? (count_ppConstantBuffers<=128 ? stack_ppConstantBuffers : HeapAlloc(GetProcessHeap(), 0, count_ppConstantBuffers*4)) : NULL;
    if (ppConstantBuffers && count_ppConstantBuffers && !tokens_ppConstantBuffers) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppConstantBuffers && ppConstantBuffers; ++i) tokens_ppConstantBuffers[i] = proxy_token(ppConstantBuffers[i]);
    packet.args[2] = guest_address(tokens_ppConstantBuffers);
    LONG status = proxy_call(&packet);
    if (tokens_ppConstantBuffers && count_ppConstantBuffers>128) HeapFree(GetProcessHeap(), 0, tokens_ppConstantBuffers);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_PSSetShaderResources(ID3D11DeviceContext *This, UINT StartSlot, UINT NumViews, ID3D11ShaderResourceView *const * ppShaderResourceViews) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 8};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumViews;
    UINT count_ppShaderResourceViews = safe_array_count(NumViews);
    uint32_t stack_ppShaderResourceViews[128];
    uint32_t *tokens_ppShaderResourceViews = ppShaderResourceViews && count_ppShaderResourceViews ? (count_ppShaderResourceViews<=128 ? stack_ppShaderResourceViews : HeapAlloc(GetProcessHeap(), 0, count_ppShaderResourceViews*4)) : NULL;
    if (ppShaderResourceViews && count_ppShaderResourceViews && !tokens_ppShaderResourceViews) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppShaderResourceViews && ppShaderResourceViews; ++i) tokens_ppShaderResourceViews[i] = proxy_token(ppShaderResourceViews[i]);
    packet.args[2] = guest_address(tokens_ppShaderResourceViews);
    LONG status = proxy_call(&packet);
    if (tokens_ppShaderResourceViews && count_ppShaderResourceViews>128) HeapFree(GetProcessHeap(), 0, tokens_ppShaderResourceViews);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_PSSetShader(ID3D11DeviceContext *This, ID3D11PixelShader * pPixelShader, ID3D11ClassInstance *const * ppClassInstances, UINT NumClassInstances) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 9};
    packet.args[0] = proxy_token(pPixelShader);
    UINT count_ppClassInstances = safe_array_count(NumClassInstances);
    uint32_t stack_ppClassInstances[128];
    uint32_t *tokens_ppClassInstances = ppClassInstances && count_ppClassInstances ? (count_ppClassInstances<=128 ? stack_ppClassInstances : HeapAlloc(GetProcessHeap(), 0, count_ppClassInstances*4)) : NULL;
    if (ppClassInstances && count_ppClassInstances && !tokens_ppClassInstances) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppClassInstances && ppClassInstances; ++i) tokens_ppClassInstances[i] = proxy_token(ppClassInstances[i]);
    packet.args[1] = guest_address(tokens_ppClassInstances);
    packet.args[2] = (uint32_t)NumClassInstances;
    LONG status = proxy_call(&packet);
    if (tokens_ppClassInstances && count_ppClassInstances>128) HeapFree(GetProcessHeap(), 0, tokens_ppClassInstances);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_PSSetSamplers(ID3D11DeviceContext *This, UINT StartSlot, UINT NumSamplers, ID3D11SamplerState *const * ppSamplers) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 10};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumSamplers;
    UINT count_ppSamplers = safe_array_count(NumSamplers);
    uint32_t stack_ppSamplers[128];
    uint32_t *tokens_ppSamplers = ppSamplers && count_ppSamplers ? (count_ppSamplers<=128 ? stack_ppSamplers : HeapAlloc(GetProcessHeap(), 0, count_ppSamplers*4)) : NULL;
    if (ppSamplers && count_ppSamplers && !tokens_ppSamplers) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppSamplers && ppSamplers; ++i) tokens_ppSamplers[i] = proxy_token(ppSamplers[i]);
    packet.args[2] = guest_address(tokens_ppSamplers);
    LONG status = proxy_call(&packet);
    if (tokens_ppSamplers && count_ppSamplers>128) HeapFree(GetProcessHeap(), 0, tokens_ppSamplers);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_VSSetShader(ID3D11DeviceContext *This, ID3D11VertexShader * pVertexShader, ID3D11ClassInstance *const * ppClassInstances, UINT NumClassInstances) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 11};
    packet.args[0] = proxy_token(pVertexShader);
    UINT count_ppClassInstances = safe_array_count(NumClassInstances);
    uint32_t stack_ppClassInstances[128];
    uint32_t *tokens_ppClassInstances = ppClassInstances && count_ppClassInstances ? (count_ppClassInstances<=128 ? stack_ppClassInstances : HeapAlloc(GetProcessHeap(), 0, count_ppClassInstances*4)) : NULL;
    if (ppClassInstances && count_ppClassInstances && !tokens_ppClassInstances) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppClassInstances && ppClassInstances; ++i) tokens_ppClassInstances[i] = proxy_token(ppClassInstances[i]);
    packet.args[1] = guest_address(tokens_ppClassInstances);
    packet.args[2] = (uint32_t)NumClassInstances;
    LONG status = proxy_call(&packet);
    if (tokens_ppClassInstances && count_ppClassInstances>128) HeapFree(GetProcessHeap(), 0, tokens_ppClassInstances);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_DrawIndexed(ID3D11DeviceContext *This, UINT IndexCount, UINT StartIndexLocation, INT BaseVertexLocation) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 12};
    packet.args[0] = (uint32_t)IndexCount;
    packet.args[1] = (uint32_t)StartIndexLocation;
    packet.args[2] = (uint32_t)BaseVertexLocation;
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_Draw(ID3D11DeviceContext *This, UINT VertexCount, UINT StartVertexLocation) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 13};
    packet.args[0] = (uint32_t)VertexCount;
    packet.args[1] = (uint32_t)StartVertexLocation;
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11DeviceContext_Map(ID3D11DeviceContext *This, ID3D11Resource * pResource, UINT Subresource, D3D11_MAP MapType, UINT MapFlags, D3D11_MAPPED_SUBRESOURCE * pMappedResource) {
    return proxy_map(This, pResource, Subresource, MapType, MapFlags, pMappedResource);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_Unmap(ID3D11DeviceContext *This, ID3D11Resource * pResource, UINT Subresource) {
    proxy_unmap(This, pResource, Subresource);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_PSSetConstantBuffers(ID3D11DeviceContext *This, UINT StartSlot, UINT NumBuffers, ID3D11Buffer *const * ppConstantBuffers) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 16};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumBuffers;
    UINT count_ppConstantBuffers = safe_array_count(NumBuffers);
    uint32_t stack_ppConstantBuffers[128];
    uint32_t *tokens_ppConstantBuffers = ppConstantBuffers && count_ppConstantBuffers ? (count_ppConstantBuffers<=128 ? stack_ppConstantBuffers : HeapAlloc(GetProcessHeap(), 0, count_ppConstantBuffers*4)) : NULL;
    if (ppConstantBuffers && count_ppConstantBuffers && !tokens_ppConstantBuffers) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppConstantBuffers && ppConstantBuffers; ++i) tokens_ppConstantBuffers[i] = proxy_token(ppConstantBuffers[i]);
    packet.args[2] = guest_address(tokens_ppConstantBuffers);
    LONG status = proxy_call(&packet);
    if (tokens_ppConstantBuffers && count_ppConstantBuffers>128) HeapFree(GetProcessHeap(), 0, tokens_ppConstantBuffers);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_IASetInputLayout(ID3D11DeviceContext *This, ID3D11InputLayout * pInputLayout) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 17};
    packet.args[0] = proxy_token(pInputLayout);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_IASetVertexBuffers(ID3D11DeviceContext *This, UINT StartSlot, UINT NumBuffers, ID3D11Buffer *const * ppVertexBuffers, const UINT * pStrides, const UINT * pOffsets) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 18};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumBuffers;
    UINT count_ppVertexBuffers = safe_array_count(NumBuffers);
    uint32_t stack_ppVertexBuffers[128];
    uint32_t *tokens_ppVertexBuffers = ppVertexBuffers && count_ppVertexBuffers ? (count_ppVertexBuffers<=128 ? stack_ppVertexBuffers : HeapAlloc(GetProcessHeap(), 0, count_ppVertexBuffers*4)) : NULL;
    if (ppVertexBuffers && count_ppVertexBuffers && !tokens_ppVertexBuffers) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppVertexBuffers && ppVertexBuffers; ++i) tokens_ppVertexBuffers[i] = proxy_token(ppVertexBuffers[i]);
    packet.args[2] = guest_address(tokens_ppVertexBuffers);
    packet.args[3] = guest_address(pStrides);
    packet.args[4] = guest_address(pOffsets);
    LONG status = proxy_call(&packet);
    if (tokens_ppVertexBuffers && count_ppVertexBuffers>128) HeapFree(GetProcessHeap(), 0, tokens_ppVertexBuffers);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_IASetIndexBuffer(ID3D11DeviceContext *This, ID3D11Buffer * pIndexBuffer, DXGI_FORMAT Format, UINT Offset) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 19};
    packet.args[0] = proxy_token(pIndexBuffer);
    packet.args[1] = (uint32_t)Format;
    packet.args[2] = (uint32_t)Offset;
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_DrawIndexedInstanced(ID3D11DeviceContext *This, UINT IndexCountPerInstance, UINT InstanceCount, UINT StartIndexLocation, INT BaseVertexLocation, UINT StartInstanceLocation) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 20};
    packet.args[0] = (uint32_t)IndexCountPerInstance;
    packet.args[1] = (uint32_t)InstanceCount;
    packet.args[2] = (uint32_t)StartIndexLocation;
    packet.args[3] = (uint32_t)BaseVertexLocation;
    packet.args[4] = (uint32_t)StartInstanceLocation;
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_DrawInstanced(ID3D11DeviceContext *This, UINT VertexCountPerInstance, UINT InstanceCount, UINT StartVertexLocation, UINT StartInstanceLocation) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 21};
    packet.args[0] = (uint32_t)VertexCountPerInstance;
    packet.args[1] = (uint32_t)InstanceCount;
    packet.args[2] = (uint32_t)StartVertexLocation;
    packet.args[3] = (uint32_t)StartInstanceLocation;
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_GSSetConstantBuffers(ID3D11DeviceContext *This, UINT StartSlot, UINT NumBuffers, ID3D11Buffer *const * ppConstantBuffers) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 22};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumBuffers;
    UINT count_ppConstantBuffers = safe_array_count(NumBuffers);
    uint32_t stack_ppConstantBuffers[128];
    uint32_t *tokens_ppConstantBuffers = ppConstantBuffers && count_ppConstantBuffers ? (count_ppConstantBuffers<=128 ? stack_ppConstantBuffers : HeapAlloc(GetProcessHeap(), 0, count_ppConstantBuffers*4)) : NULL;
    if (ppConstantBuffers && count_ppConstantBuffers && !tokens_ppConstantBuffers) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppConstantBuffers && ppConstantBuffers; ++i) tokens_ppConstantBuffers[i] = proxy_token(ppConstantBuffers[i]);
    packet.args[2] = guest_address(tokens_ppConstantBuffers);
    LONG status = proxy_call(&packet);
    if (tokens_ppConstantBuffers && count_ppConstantBuffers>128) HeapFree(GetProcessHeap(), 0, tokens_ppConstantBuffers);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_GSSetShader(ID3D11DeviceContext *This, ID3D11GeometryShader * pShader, ID3D11ClassInstance *const * ppClassInstances, UINT NumClassInstances) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 23};
    packet.args[0] = proxy_token(pShader);
    UINT count_ppClassInstances = safe_array_count(NumClassInstances);
    uint32_t stack_ppClassInstances[128];
    uint32_t *tokens_ppClassInstances = ppClassInstances && count_ppClassInstances ? (count_ppClassInstances<=128 ? stack_ppClassInstances : HeapAlloc(GetProcessHeap(), 0, count_ppClassInstances*4)) : NULL;
    if (ppClassInstances && count_ppClassInstances && !tokens_ppClassInstances) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppClassInstances && ppClassInstances; ++i) tokens_ppClassInstances[i] = proxy_token(ppClassInstances[i]);
    packet.args[1] = guest_address(tokens_ppClassInstances);
    packet.args[2] = (uint32_t)NumClassInstances;
    LONG status = proxy_call(&packet);
    if (tokens_ppClassInstances && count_ppClassInstances>128) HeapFree(GetProcessHeap(), 0, tokens_ppClassInstances);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_IASetPrimitiveTopology(ID3D11DeviceContext *This, D3D11_PRIMITIVE_TOPOLOGY Topology) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 24};
    packet.args[0] = (uint32_t)Topology;
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_VSSetShaderResources(ID3D11DeviceContext *This, UINT StartSlot, UINT NumViews, ID3D11ShaderResourceView *const * ppShaderResourceViews) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 25};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumViews;
    UINT count_ppShaderResourceViews = safe_array_count(NumViews);
    uint32_t stack_ppShaderResourceViews[128];
    uint32_t *tokens_ppShaderResourceViews = ppShaderResourceViews && count_ppShaderResourceViews ? (count_ppShaderResourceViews<=128 ? stack_ppShaderResourceViews : HeapAlloc(GetProcessHeap(), 0, count_ppShaderResourceViews*4)) : NULL;
    if (ppShaderResourceViews && count_ppShaderResourceViews && !tokens_ppShaderResourceViews) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppShaderResourceViews && ppShaderResourceViews; ++i) tokens_ppShaderResourceViews[i] = proxy_token(ppShaderResourceViews[i]);
    packet.args[2] = guest_address(tokens_ppShaderResourceViews);
    LONG status = proxy_call(&packet);
    if (tokens_ppShaderResourceViews && count_ppShaderResourceViews>128) HeapFree(GetProcessHeap(), 0, tokens_ppShaderResourceViews);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_VSSetSamplers(ID3D11DeviceContext *This, UINT StartSlot, UINT NumSamplers, ID3D11SamplerState *const * ppSamplers) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 26};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumSamplers;
    UINT count_ppSamplers = safe_array_count(NumSamplers);
    uint32_t stack_ppSamplers[128];
    uint32_t *tokens_ppSamplers = ppSamplers && count_ppSamplers ? (count_ppSamplers<=128 ? stack_ppSamplers : HeapAlloc(GetProcessHeap(), 0, count_ppSamplers*4)) : NULL;
    if (ppSamplers && count_ppSamplers && !tokens_ppSamplers) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppSamplers && ppSamplers; ++i) tokens_ppSamplers[i] = proxy_token(ppSamplers[i]);
    packet.args[2] = guest_address(tokens_ppSamplers);
    LONG status = proxy_call(&packet);
    if (tokens_ppSamplers && count_ppSamplers>128) HeapFree(GetProcessHeap(), 0, tokens_ppSamplers);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_Begin(ID3D11DeviceContext *This, ID3D11Asynchronous * pAsync) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 27};
    packet.args[0] = proxy_token(pAsync);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_End(ID3D11DeviceContext *This, ID3D11Asynchronous * pAsync) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 28};
    packet.args[0] = proxy_token(pAsync);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11DeviceContext_GetData(ID3D11DeviceContext *This, ID3D11Asynchronous * pAsync, void * pData, UINT DataSize, UINT GetDataFlags) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 29};
    packet.args[0] = proxy_token(pAsync);
    packet.args[1] = guest_address(pData);
    packet.args[2] = (uint32_t)DataSize;
    packet.args[3] = (uint32_t)GetDataFlags;
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_SetPredication(ID3D11DeviceContext *This, ID3D11Predicate * pPredicate, WINBOOL PredicateValue) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 30};
    packet.args[0] = proxy_token(pPredicate);
    packet.args[1] = (uint32_t)PredicateValue;
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_GSSetShaderResources(ID3D11DeviceContext *This, UINT StartSlot, UINT NumViews, ID3D11ShaderResourceView *const * ppShaderResourceViews) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 31};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumViews;
    UINT count_ppShaderResourceViews = safe_array_count(NumViews);
    uint32_t stack_ppShaderResourceViews[128];
    uint32_t *tokens_ppShaderResourceViews = ppShaderResourceViews && count_ppShaderResourceViews ? (count_ppShaderResourceViews<=128 ? stack_ppShaderResourceViews : HeapAlloc(GetProcessHeap(), 0, count_ppShaderResourceViews*4)) : NULL;
    if (ppShaderResourceViews && count_ppShaderResourceViews && !tokens_ppShaderResourceViews) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppShaderResourceViews && ppShaderResourceViews; ++i) tokens_ppShaderResourceViews[i] = proxy_token(ppShaderResourceViews[i]);
    packet.args[2] = guest_address(tokens_ppShaderResourceViews);
    LONG status = proxy_call(&packet);
    if (tokens_ppShaderResourceViews && count_ppShaderResourceViews>128) HeapFree(GetProcessHeap(), 0, tokens_ppShaderResourceViews);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_GSSetSamplers(ID3D11DeviceContext *This, UINT StartSlot, UINT NumSamplers, ID3D11SamplerState *const * ppSamplers) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 32};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumSamplers;
    UINT count_ppSamplers = safe_array_count(NumSamplers);
    uint32_t stack_ppSamplers[128];
    uint32_t *tokens_ppSamplers = ppSamplers && count_ppSamplers ? (count_ppSamplers<=128 ? stack_ppSamplers : HeapAlloc(GetProcessHeap(), 0, count_ppSamplers*4)) : NULL;
    if (ppSamplers && count_ppSamplers && !tokens_ppSamplers) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppSamplers && ppSamplers; ++i) tokens_ppSamplers[i] = proxy_token(ppSamplers[i]);
    packet.args[2] = guest_address(tokens_ppSamplers);
    LONG status = proxy_call(&packet);
    if (tokens_ppSamplers && count_ppSamplers>128) HeapFree(GetProcessHeap(), 0, tokens_ppSamplers);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_OMSetRenderTargets(ID3D11DeviceContext *This, UINT NumViews, ID3D11RenderTargetView *const * ppRenderTargetViews, ID3D11DepthStencilView * pDepthStencilView) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 33};
    packet.args[0] = (uint32_t)NumViews;
    UINT count_ppRenderTargetViews = safe_array_count(NumViews);
    uint32_t stack_ppRenderTargetViews[128];
    uint32_t *tokens_ppRenderTargetViews = ppRenderTargetViews && count_ppRenderTargetViews ? (count_ppRenderTargetViews<=128 ? stack_ppRenderTargetViews : HeapAlloc(GetProcessHeap(), 0, count_ppRenderTargetViews*4)) : NULL;
    if (ppRenderTargetViews && count_ppRenderTargetViews && !tokens_ppRenderTargetViews) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppRenderTargetViews && ppRenderTargetViews; ++i) tokens_ppRenderTargetViews[i] = proxy_token(ppRenderTargetViews[i]);
    packet.args[1] = guest_address(tokens_ppRenderTargetViews);
    packet.args[2] = proxy_token(pDepthStencilView);
    LONG status = proxy_call(&packet);
    if (tokens_ppRenderTargetViews && count_ppRenderTargetViews>128) HeapFree(GetProcessHeap(), 0, tokens_ppRenderTargetViews);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_OMSetRenderTargetsAndUnorderedAccessViews(ID3D11DeviceContext *This, UINT NumRTVs, ID3D11RenderTargetView *const * ppRenderTargetViews, ID3D11DepthStencilView * pDepthStencilView, UINT UAVStartSlot, UINT NumUAVs, ID3D11UnorderedAccessView *const * ppUnorderedAccessViews, const UINT * pUAVInitialCounts) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 34};
    packet.args[0] = (uint32_t)NumRTVs;
    UINT count_ppRenderTargetViews = safe_array_count(NumRTVs);
    uint32_t stack_ppRenderTargetViews[128];
    uint32_t *tokens_ppRenderTargetViews = ppRenderTargetViews && count_ppRenderTargetViews ? (count_ppRenderTargetViews<=128 ? stack_ppRenderTargetViews : HeapAlloc(GetProcessHeap(), 0, count_ppRenderTargetViews*4)) : NULL;
    if (ppRenderTargetViews && count_ppRenderTargetViews && !tokens_ppRenderTargetViews) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppRenderTargetViews && ppRenderTargetViews; ++i) tokens_ppRenderTargetViews[i] = proxy_token(ppRenderTargetViews[i]);
    packet.args[1] = guest_address(tokens_ppRenderTargetViews);
    packet.args[2] = proxy_token(pDepthStencilView);
    packet.args[3] = (uint32_t)UAVStartSlot;
    packet.args[4] = (uint32_t)NumUAVs;
    UINT count_ppUnorderedAccessViews = safe_array_count(NumUAVs);
    uint32_t stack_ppUnorderedAccessViews[128];
    uint32_t *tokens_ppUnorderedAccessViews = ppUnorderedAccessViews && count_ppUnorderedAccessViews ? (count_ppUnorderedAccessViews<=128 ? stack_ppUnorderedAccessViews : HeapAlloc(GetProcessHeap(), 0, count_ppUnorderedAccessViews*4)) : NULL;
    if (ppUnorderedAccessViews && count_ppUnorderedAccessViews && !tokens_ppUnorderedAccessViews) { if(tokens_ppRenderTargetViews && count_ppRenderTargetViews>128) HeapFree(GetProcessHeap(),0,tokens_ppRenderTargetViews); proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppUnorderedAccessViews && ppUnorderedAccessViews; ++i) tokens_ppUnorderedAccessViews[i] = proxy_token(ppUnorderedAccessViews[i]);
    packet.args[5] = guest_address(tokens_ppUnorderedAccessViews);
    packet.args[6] = guest_address(pUAVInitialCounts);
    LONG status = proxy_call(&packet);
    if (tokens_ppRenderTargetViews && count_ppRenderTargetViews>128) HeapFree(GetProcessHeap(), 0, tokens_ppRenderTargetViews);
    if (tokens_ppUnorderedAccessViews && count_ppUnorderedAccessViews>128) HeapFree(GetProcessHeap(), 0, tokens_ppUnorderedAccessViews);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_OMSetBlendState(ID3D11DeviceContext *This, ID3D11BlendState * pBlendState, const FLOAT BlendFactor[4], UINT SampleMask) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 35};
    packet.args[0] = proxy_token(pBlendState);
    packet.args[1] = guest_address(BlendFactor);
    packet.args[2] = (uint32_t)SampleMask;
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_OMSetDepthStencilState(ID3D11DeviceContext *This, ID3D11DepthStencilState * pDepthStencilState, UINT StencilRef) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 36};
    packet.args[0] = proxy_token(pDepthStencilState);
    packet.args[1] = (uint32_t)StencilRef;
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_SOSetTargets(ID3D11DeviceContext *This, UINT NumBuffers, ID3D11Buffer *const * ppSOTargets, const UINT * pOffsets) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 37};
    packet.args[0] = (uint32_t)NumBuffers;
    UINT count_ppSOTargets = safe_array_count(NumBuffers);
    uint32_t stack_ppSOTargets[128];
    uint32_t *tokens_ppSOTargets = ppSOTargets && count_ppSOTargets ? (count_ppSOTargets<=128 ? stack_ppSOTargets : HeapAlloc(GetProcessHeap(), 0, count_ppSOTargets*4)) : NULL;
    if (ppSOTargets && count_ppSOTargets && !tokens_ppSOTargets) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppSOTargets && ppSOTargets; ++i) tokens_ppSOTargets[i] = proxy_token(ppSOTargets[i]);
    packet.args[1] = guest_address(tokens_ppSOTargets);
    packet.args[2] = guest_address(pOffsets);
    LONG status = proxy_call(&packet);
    if (tokens_ppSOTargets && count_ppSOTargets>128) HeapFree(GetProcessHeap(), 0, tokens_ppSOTargets);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_DrawAuto(ID3D11DeviceContext *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 38};
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_DrawIndexedInstancedIndirect(ID3D11DeviceContext *This, ID3D11Buffer * pBufferForArgs, UINT AlignedByteOffsetForArgs) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 39};
    packet.args[0] = proxy_token(pBufferForArgs);
    packet.args[1] = (uint32_t)AlignedByteOffsetForArgs;
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_DrawInstancedIndirect(ID3D11DeviceContext *This, ID3D11Buffer * pBufferForArgs, UINT AlignedByteOffsetForArgs) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 40};
    packet.args[0] = proxy_token(pBufferForArgs);
    packet.args[1] = (uint32_t)AlignedByteOffsetForArgs;
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_Dispatch(ID3D11DeviceContext *This, UINT ThreadGroupCountX, UINT ThreadGroupCountY, UINT ThreadGroupCountZ) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 41};
    packet.args[0] = (uint32_t)ThreadGroupCountX;
    packet.args[1] = (uint32_t)ThreadGroupCountY;
    packet.args[2] = (uint32_t)ThreadGroupCountZ;
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_DispatchIndirect(ID3D11DeviceContext *This, ID3D11Buffer * pBufferForArgs, UINT AlignedByteOffsetForArgs) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 42};
    packet.args[0] = proxy_token(pBufferForArgs);
    packet.args[1] = (uint32_t)AlignedByteOffsetForArgs;
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_RSSetState(ID3D11DeviceContext *This, ID3D11RasterizerState * pRasterizerState) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 43};
    packet.args[0] = proxy_token(pRasterizerState);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_RSSetViewports(ID3D11DeviceContext *This, UINT NumViewports, const D3D11_VIEWPORT * pViewports) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 44};
    packet.args[0] = (uint32_t)NumViewports;
    packet.args[1] = guest_address(pViewports);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_RSSetScissorRects(ID3D11DeviceContext *This, UINT NumRects, const D3D11_RECT * pRects) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 45};
    packet.args[0] = (uint32_t)NumRects;
    packet.args[1] = guest_address(pRects);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_CopySubresourceRegion(ID3D11DeviceContext *This, ID3D11Resource * pDstResource, UINT DstSubresource, UINT DstX, UINT DstY, UINT DstZ, ID3D11Resource * pSrcResource, UINT SrcSubresource, const D3D11_BOX * pSrcBox) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 46};
    packet.args[0] = proxy_token(pDstResource);
    packet.args[1] = (uint32_t)DstSubresource;
    packet.args[2] = (uint32_t)DstX;
    packet.args[3] = (uint32_t)DstY;
    packet.args[4] = (uint32_t)DstZ;
    packet.args[5] = proxy_token(pSrcResource);
    packet.args[6] = (uint32_t)SrcSubresource;
    packet.args[7] = guest_address(pSrcBox);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_CopyResource(ID3D11DeviceContext *This, ID3D11Resource * pDstResource, ID3D11Resource * pSrcResource) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 47};
    packet.args[0] = proxy_token(pDstResource);
    packet.args[1] = proxy_token(pSrcResource);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_UpdateSubresource(ID3D11DeviceContext *This, ID3D11Resource * pDstResource, UINT DstSubresource, const D3D11_BOX * pDstBox, const void * pSrcData, UINT SrcRowPitch, UINT SrcDepthPitch) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 48};
    packet.args[0] = proxy_token(pDstResource);
    packet.args[1] = (uint32_t)DstSubresource;
    packet.args[2] = guest_address(pDstBox);
    packet.args[3] = guest_address(pSrcData);
    packet.args[4] = (uint32_t)SrcRowPitch;
    packet.args[5] = (uint32_t)SrcDepthPitch;
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_CopyStructureCount(ID3D11DeviceContext *This, ID3D11Buffer * pDstBuffer, UINT DstAlignedByteOffset, ID3D11UnorderedAccessView * pSrcView) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 49};
    packet.args[0] = proxy_token(pDstBuffer);
    packet.args[1] = (uint32_t)DstAlignedByteOffset;
    packet.args[2] = proxy_token(pSrcView);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_ClearRenderTargetView(ID3D11DeviceContext *This, ID3D11RenderTargetView * pRenderTargetView, const FLOAT ColorRGBA[4]) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 50};
    packet.args[0] = proxy_token(pRenderTargetView);
    packet.args[1] = guest_address(ColorRGBA);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_ClearUnorderedAccessViewUint(ID3D11DeviceContext *This, ID3D11UnorderedAccessView * pUnorderedAccessView, const UINT Values[4]) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 51};
    packet.args[0] = proxy_token(pUnorderedAccessView);
    packet.args[1] = guest_address(Values);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_ClearUnorderedAccessViewFloat(ID3D11DeviceContext *This, ID3D11UnorderedAccessView * pUnorderedAccessView, const FLOAT Values[4]) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 52};
    packet.args[0] = proxy_token(pUnorderedAccessView);
    packet.args[1] = guest_address(Values);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_ClearDepthStencilView(ID3D11DeviceContext *This, ID3D11DepthStencilView * pDepthStencilView, UINT ClearFlags, FLOAT Depth, UINT8 Stencil) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 53};
    packet.args[0] = proxy_token(pDepthStencilView);
    packet.args[1] = (uint32_t)ClearFlags;
    packet.args[2] = float_bits(Depth);
    packet.args[3] = (uint32_t)Stencil;
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_GenerateMips(ID3D11DeviceContext *This, ID3D11ShaderResourceView * pShaderResourceView) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 54};
    packet.args[0] = proxy_token(pShaderResourceView);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_SetResourceMinLOD(ID3D11DeviceContext *This, ID3D11Resource * pResource, FLOAT MinLOD) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 55};
    packet.args[0] = proxy_token(pResource);
    packet.args[1] = float_bits(MinLOD);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static FLOAT STDMETHODCALLTYPE g_ID3D11DeviceContext_GetResourceMinLOD(ID3D11DeviceContext *This, ID3D11Resource * pResource) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 56};
    packet.args[0] = proxy_token(pResource);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (FLOAT)status; }
    return bits_float(packet.ret);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_ResolveSubresource(ID3D11DeviceContext *This, ID3D11Resource * pDstResource, UINT DstSubresource, ID3D11Resource * pSrcResource, UINT SrcSubresource, DXGI_FORMAT Format) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 57};
    packet.args[0] = proxy_token(pDstResource);
    packet.args[1] = (uint32_t)DstSubresource;
    packet.args[2] = proxy_token(pSrcResource);
    packet.args[3] = (uint32_t)SrcSubresource;
    packet.args[4] = (uint32_t)Format;
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_ExecuteCommandList(ID3D11DeviceContext *This, ID3D11CommandList * pCommandList, WINBOOL RestoreContextState) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 58};
    packet.args[0] = proxy_token(pCommandList);
    packet.args[1] = (uint32_t)RestoreContextState;
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_HSSetShaderResources(ID3D11DeviceContext *This, UINT StartSlot, UINT NumViews, ID3D11ShaderResourceView *const * ppShaderResourceViews) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 59};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumViews;
    UINT count_ppShaderResourceViews = safe_array_count(NumViews);
    uint32_t stack_ppShaderResourceViews[128];
    uint32_t *tokens_ppShaderResourceViews = ppShaderResourceViews && count_ppShaderResourceViews ? (count_ppShaderResourceViews<=128 ? stack_ppShaderResourceViews : HeapAlloc(GetProcessHeap(), 0, count_ppShaderResourceViews*4)) : NULL;
    if (ppShaderResourceViews && count_ppShaderResourceViews && !tokens_ppShaderResourceViews) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppShaderResourceViews && ppShaderResourceViews; ++i) tokens_ppShaderResourceViews[i] = proxy_token(ppShaderResourceViews[i]);
    packet.args[2] = guest_address(tokens_ppShaderResourceViews);
    LONG status = proxy_call(&packet);
    if (tokens_ppShaderResourceViews && count_ppShaderResourceViews>128) HeapFree(GetProcessHeap(), 0, tokens_ppShaderResourceViews);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_HSSetShader(ID3D11DeviceContext *This, ID3D11HullShader * pHullShader, ID3D11ClassInstance *const * ppClassInstances, UINT NumClassInstances) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 60};
    packet.args[0] = proxy_token(pHullShader);
    UINT count_ppClassInstances = safe_array_count(NumClassInstances);
    uint32_t stack_ppClassInstances[128];
    uint32_t *tokens_ppClassInstances = ppClassInstances && count_ppClassInstances ? (count_ppClassInstances<=128 ? stack_ppClassInstances : HeapAlloc(GetProcessHeap(), 0, count_ppClassInstances*4)) : NULL;
    if (ppClassInstances && count_ppClassInstances && !tokens_ppClassInstances) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppClassInstances && ppClassInstances; ++i) tokens_ppClassInstances[i] = proxy_token(ppClassInstances[i]);
    packet.args[1] = guest_address(tokens_ppClassInstances);
    packet.args[2] = (uint32_t)NumClassInstances;
    LONG status = proxy_call(&packet);
    if (tokens_ppClassInstances && count_ppClassInstances>128) HeapFree(GetProcessHeap(), 0, tokens_ppClassInstances);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_HSSetSamplers(ID3D11DeviceContext *This, UINT StartSlot, UINT NumSamplers, ID3D11SamplerState *const * ppSamplers) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 61};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumSamplers;
    UINT count_ppSamplers = safe_array_count(NumSamplers);
    uint32_t stack_ppSamplers[128];
    uint32_t *tokens_ppSamplers = ppSamplers && count_ppSamplers ? (count_ppSamplers<=128 ? stack_ppSamplers : HeapAlloc(GetProcessHeap(), 0, count_ppSamplers*4)) : NULL;
    if (ppSamplers && count_ppSamplers && !tokens_ppSamplers) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppSamplers && ppSamplers; ++i) tokens_ppSamplers[i] = proxy_token(ppSamplers[i]);
    packet.args[2] = guest_address(tokens_ppSamplers);
    LONG status = proxy_call(&packet);
    if (tokens_ppSamplers && count_ppSamplers>128) HeapFree(GetProcessHeap(), 0, tokens_ppSamplers);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_HSSetConstantBuffers(ID3D11DeviceContext *This, UINT StartSlot, UINT NumBuffers, ID3D11Buffer *const * ppConstantBuffers) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 62};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumBuffers;
    UINT count_ppConstantBuffers = safe_array_count(NumBuffers);
    uint32_t stack_ppConstantBuffers[128];
    uint32_t *tokens_ppConstantBuffers = ppConstantBuffers && count_ppConstantBuffers ? (count_ppConstantBuffers<=128 ? stack_ppConstantBuffers : HeapAlloc(GetProcessHeap(), 0, count_ppConstantBuffers*4)) : NULL;
    if (ppConstantBuffers && count_ppConstantBuffers && !tokens_ppConstantBuffers) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppConstantBuffers && ppConstantBuffers; ++i) tokens_ppConstantBuffers[i] = proxy_token(ppConstantBuffers[i]);
    packet.args[2] = guest_address(tokens_ppConstantBuffers);
    LONG status = proxy_call(&packet);
    if (tokens_ppConstantBuffers && count_ppConstantBuffers>128) HeapFree(GetProcessHeap(), 0, tokens_ppConstantBuffers);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_DSSetShaderResources(ID3D11DeviceContext *This, UINT StartSlot, UINT NumViews, ID3D11ShaderResourceView *const * ppShaderResourceViews) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 63};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumViews;
    UINT count_ppShaderResourceViews = safe_array_count(NumViews);
    uint32_t stack_ppShaderResourceViews[128];
    uint32_t *tokens_ppShaderResourceViews = ppShaderResourceViews && count_ppShaderResourceViews ? (count_ppShaderResourceViews<=128 ? stack_ppShaderResourceViews : HeapAlloc(GetProcessHeap(), 0, count_ppShaderResourceViews*4)) : NULL;
    if (ppShaderResourceViews && count_ppShaderResourceViews && !tokens_ppShaderResourceViews) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppShaderResourceViews && ppShaderResourceViews; ++i) tokens_ppShaderResourceViews[i] = proxy_token(ppShaderResourceViews[i]);
    packet.args[2] = guest_address(tokens_ppShaderResourceViews);
    LONG status = proxy_call(&packet);
    if (tokens_ppShaderResourceViews && count_ppShaderResourceViews>128) HeapFree(GetProcessHeap(), 0, tokens_ppShaderResourceViews);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_DSSetShader(ID3D11DeviceContext *This, ID3D11DomainShader * pDomainShader, ID3D11ClassInstance *const * ppClassInstances, UINT NumClassInstances) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 64};
    packet.args[0] = proxy_token(pDomainShader);
    UINT count_ppClassInstances = safe_array_count(NumClassInstances);
    uint32_t stack_ppClassInstances[128];
    uint32_t *tokens_ppClassInstances = ppClassInstances && count_ppClassInstances ? (count_ppClassInstances<=128 ? stack_ppClassInstances : HeapAlloc(GetProcessHeap(), 0, count_ppClassInstances*4)) : NULL;
    if (ppClassInstances && count_ppClassInstances && !tokens_ppClassInstances) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppClassInstances && ppClassInstances; ++i) tokens_ppClassInstances[i] = proxy_token(ppClassInstances[i]);
    packet.args[1] = guest_address(tokens_ppClassInstances);
    packet.args[2] = (uint32_t)NumClassInstances;
    LONG status = proxy_call(&packet);
    if (tokens_ppClassInstances && count_ppClassInstances>128) HeapFree(GetProcessHeap(), 0, tokens_ppClassInstances);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_DSSetSamplers(ID3D11DeviceContext *This, UINT StartSlot, UINT NumSamplers, ID3D11SamplerState *const * ppSamplers) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 65};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumSamplers;
    UINT count_ppSamplers = safe_array_count(NumSamplers);
    uint32_t stack_ppSamplers[128];
    uint32_t *tokens_ppSamplers = ppSamplers && count_ppSamplers ? (count_ppSamplers<=128 ? stack_ppSamplers : HeapAlloc(GetProcessHeap(), 0, count_ppSamplers*4)) : NULL;
    if (ppSamplers && count_ppSamplers && !tokens_ppSamplers) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppSamplers && ppSamplers; ++i) tokens_ppSamplers[i] = proxy_token(ppSamplers[i]);
    packet.args[2] = guest_address(tokens_ppSamplers);
    LONG status = proxy_call(&packet);
    if (tokens_ppSamplers && count_ppSamplers>128) HeapFree(GetProcessHeap(), 0, tokens_ppSamplers);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_DSSetConstantBuffers(ID3D11DeviceContext *This, UINT StartSlot, UINT NumBuffers, ID3D11Buffer *const * ppConstantBuffers) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 66};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumBuffers;
    UINT count_ppConstantBuffers = safe_array_count(NumBuffers);
    uint32_t stack_ppConstantBuffers[128];
    uint32_t *tokens_ppConstantBuffers = ppConstantBuffers && count_ppConstantBuffers ? (count_ppConstantBuffers<=128 ? stack_ppConstantBuffers : HeapAlloc(GetProcessHeap(), 0, count_ppConstantBuffers*4)) : NULL;
    if (ppConstantBuffers && count_ppConstantBuffers && !tokens_ppConstantBuffers) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppConstantBuffers && ppConstantBuffers; ++i) tokens_ppConstantBuffers[i] = proxy_token(ppConstantBuffers[i]);
    packet.args[2] = guest_address(tokens_ppConstantBuffers);
    LONG status = proxy_call(&packet);
    if (tokens_ppConstantBuffers && count_ppConstantBuffers>128) HeapFree(GetProcessHeap(), 0, tokens_ppConstantBuffers);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_CSSetShaderResources(ID3D11DeviceContext *This, UINT StartSlot, UINT NumViews, ID3D11ShaderResourceView *const * ppShaderResourceViews) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 67};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumViews;
    UINT count_ppShaderResourceViews = safe_array_count(NumViews);
    uint32_t stack_ppShaderResourceViews[128];
    uint32_t *tokens_ppShaderResourceViews = ppShaderResourceViews && count_ppShaderResourceViews ? (count_ppShaderResourceViews<=128 ? stack_ppShaderResourceViews : HeapAlloc(GetProcessHeap(), 0, count_ppShaderResourceViews*4)) : NULL;
    if (ppShaderResourceViews && count_ppShaderResourceViews && !tokens_ppShaderResourceViews) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppShaderResourceViews && ppShaderResourceViews; ++i) tokens_ppShaderResourceViews[i] = proxy_token(ppShaderResourceViews[i]);
    packet.args[2] = guest_address(tokens_ppShaderResourceViews);
    LONG status = proxy_call(&packet);
    if (tokens_ppShaderResourceViews && count_ppShaderResourceViews>128) HeapFree(GetProcessHeap(), 0, tokens_ppShaderResourceViews);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_CSSetUnorderedAccessViews(ID3D11DeviceContext *This, UINT StartSlot, UINT NumUAVs, ID3D11UnorderedAccessView *const * ppUnorderedAccessViews, const UINT * pUAVInitialCounts) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 68};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumUAVs;
    UINT count_ppUnorderedAccessViews = safe_array_count(NumUAVs);
    uint32_t stack_ppUnorderedAccessViews[128];
    uint32_t *tokens_ppUnorderedAccessViews = ppUnorderedAccessViews && count_ppUnorderedAccessViews ? (count_ppUnorderedAccessViews<=128 ? stack_ppUnorderedAccessViews : HeapAlloc(GetProcessHeap(), 0, count_ppUnorderedAccessViews*4)) : NULL;
    if (ppUnorderedAccessViews && count_ppUnorderedAccessViews && !tokens_ppUnorderedAccessViews) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppUnorderedAccessViews && ppUnorderedAccessViews; ++i) tokens_ppUnorderedAccessViews[i] = proxy_token(ppUnorderedAccessViews[i]);
    packet.args[2] = guest_address(tokens_ppUnorderedAccessViews);
    packet.args[3] = guest_address(pUAVInitialCounts);
    LONG status = proxy_call(&packet);
    if (tokens_ppUnorderedAccessViews && count_ppUnorderedAccessViews>128) HeapFree(GetProcessHeap(), 0, tokens_ppUnorderedAccessViews);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_CSSetShader(ID3D11DeviceContext *This, ID3D11ComputeShader * pComputeShader, ID3D11ClassInstance *const * ppClassInstances, UINT NumClassInstances) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 69};
    packet.args[0] = proxy_token(pComputeShader);
    UINT count_ppClassInstances = safe_array_count(NumClassInstances);
    uint32_t stack_ppClassInstances[128];
    uint32_t *tokens_ppClassInstances = ppClassInstances && count_ppClassInstances ? (count_ppClassInstances<=128 ? stack_ppClassInstances : HeapAlloc(GetProcessHeap(), 0, count_ppClassInstances*4)) : NULL;
    if (ppClassInstances && count_ppClassInstances && !tokens_ppClassInstances) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppClassInstances && ppClassInstances; ++i) tokens_ppClassInstances[i] = proxy_token(ppClassInstances[i]);
    packet.args[1] = guest_address(tokens_ppClassInstances);
    packet.args[2] = (uint32_t)NumClassInstances;
    LONG status = proxy_call(&packet);
    if (tokens_ppClassInstances && count_ppClassInstances>128) HeapFree(GetProcessHeap(), 0, tokens_ppClassInstances);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_CSSetSamplers(ID3D11DeviceContext *This, UINT StartSlot, UINT NumSamplers, ID3D11SamplerState *const * ppSamplers) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 70};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumSamplers;
    UINT count_ppSamplers = safe_array_count(NumSamplers);
    uint32_t stack_ppSamplers[128];
    uint32_t *tokens_ppSamplers = ppSamplers && count_ppSamplers ? (count_ppSamplers<=128 ? stack_ppSamplers : HeapAlloc(GetProcessHeap(), 0, count_ppSamplers*4)) : NULL;
    if (ppSamplers && count_ppSamplers && !tokens_ppSamplers) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppSamplers && ppSamplers; ++i) tokens_ppSamplers[i] = proxy_token(ppSamplers[i]);
    packet.args[2] = guest_address(tokens_ppSamplers);
    LONG status = proxy_call(&packet);
    if (tokens_ppSamplers && count_ppSamplers>128) HeapFree(GetProcessHeap(), 0, tokens_ppSamplers);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_CSSetConstantBuffers(ID3D11DeviceContext *This, UINT StartSlot, UINT NumBuffers, ID3D11Buffer *const * ppConstantBuffers) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 71};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumBuffers;
    UINT count_ppConstantBuffers = safe_array_count(NumBuffers);
    uint32_t stack_ppConstantBuffers[128];
    uint32_t *tokens_ppConstantBuffers = ppConstantBuffers && count_ppConstantBuffers ? (count_ppConstantBuffers<=128 ? stack_ppConstantBuffers : HeapAlloc(GetProcessHeap(), 0, count_ppConstantBuffers*4)) : NULL;
    if (ppConstantBuffers && count_ppConstantBuffers && !tokens_ppConstantBuffers) {  proxy_fatal(E_OUTOFMEMORY); return; }
    for (UINT i=0; i<count_ppConstantBuffers && ppConstantBuffers; ++i) tokens_ppConstantBuffers[i] = proxy_token(ppConstantBuffers[i]);
    packet.args[2] = guest_address(tokens_ppConstantBuffers);
    LONG status = proxy_call(&packet);
    if (tokens_ppConstantBuffers && count_ppConstantBuffers>128) HeapFree(GetProcessHeap(), 0, tokens_ppConstantBuffers);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_VSGetConstantBuffers(ID3D11DeviceContext *This, UINT StartSlot, UINT NumBuffers, ID3D11Buffer ** ppConstantBuffers) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 72};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumBuffers;
    struct proxy_output wire_ppConstantBuffers;
    if (!proxy_output_init(&wire_ppConstantBuffers,ppConstantBuffers,safe_array_count(NumBuffers))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[2] = guest_address(wire_ppConstantBuffers.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppConstantBuffers,ppConstantBuffers,safe_array_count(NumBuffers),SD_COM_IF_ID3D11Buffer)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppConstantBuffers,ppConstantBuffers);
    proxy_output_dispose(&wire_ppConstantBuffers,SD_COM_IF_ID3D11Buffer);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_PSGetShaderResources(ID3D11DeviceContext *This, UINT StartSlot, UINT NumViews, ID3D11ShaderResourceView ** ppShaderResourceViews) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 73};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumViews;
    struct proxy_output wire_ppShaderResourceViews;
    if (!proxy_output_init(&wire_ppShaderResourceViews,ppShaderResourceViews,safe_array_count(NumViews))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[2] = guest_address(wire_ppShaderResourceViews.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppShaderResourceViews,ppShaderResourceViews,safe_array_count(NumViews),SD_COM_IF_ID3D11ShaderResourceView)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppShaderResourceViews,ppShaderResourceViews);
    proxy_output_dispose(&wire_ppShaderResourceViews,SD_COM_IF_ID3D11ShaderResourceView);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_PSGetShader(ID3D11DeviceContext *This, ID3D11PixelShader ** ppPixelShader, ID3D11ClassInstance ** ppClassInstances, UINT * pNumClassInstances) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 74};
    struct proxy_output wire_ppPixelShader;
    if (!proxy_output_init(&wire_ppPixelShader,ppPixelShader,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppPixelShader.tokens);
    struct proxy_output wire_ppClassInstances;
    if (!proxy_output_init(&wire_ppClassInstances,ppClassInstances,safe_array_count((pNumClassInstances ? *pNumClassInstances : 0)))) { proxy_output_dispose(&wire_ppPixelShader,SD_COM_IF_ID3D11PixelShader); proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[1] = guest_address(wire_ppClassInstances.tokens);
    packet.args[2] = guest_address(pNumClassInstances);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppPixelShader,ppPixelShader,safe_array_count(1),SD_COM_IF_ID3D11PixelShader)) status=E_OUTOFMEMORY;
    if (status >= 0 && !proxy_output_publish(&wire_ppClassInstances,ppClassInstances,safe_array_count((pNumClassInstances ? *pNumClassInstances : 0)),SD_COM_IF_ID3D11ClassInstance)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppPixelShader,ppPixelShader);
    proxy_output_dispose(&wire_ppPixelShader,SD_COM_IF_ID3D11PixelShader);
    if (!(status >= 0)) proxy_output_retract(&wire_ppClassInstances,ppClassInstances);
    proxy_output_dispose(&wire_ppClassInstances,SD_COM_IF_ID3D11ClassInstance);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_PSGetSamplers(ID3D11DeviceContext *This, UINT StartSlot, UINT NumSamplers, ID3D11SamplerState ** ppSamplers) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 75};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumSamplers;
    struct proxy_output wire_ppSamplers;
    if (!proxy_output_init(&wire_ppSamplers,ppSamplers,safe_array_count(NumSamplers))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[2] = guest_address(wire_ppSamplers.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppSamplers,ppSamplers,safe_array_count(NumSamplers),SD_COM_IF_ID3D11SamplerState)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppSamplers,ppSamplers);
    proxy_output_dispose(&wire_ppSamplers,SD_COM_IF_ID3D11SamplerState);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_VSGetShader(ID3D11DeviceContext *This, ID3D11VertexShader ** ppVertexShader, ID3D11ClassInstance ** ppClassInstances, UINT * pNumClassInstances) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 76};
    struct proxy_output wire_ppVertexShader;
    if (!proxy_output_init(&wire_ppVertexShader,ppVertexShader,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppVertexShader.tokens);
    struct proxy_output wire_ppClassInstances;
    if (!proxy_output_init(&wire_ppClassInstances,ppClassInstances,safe_array_count((pNumClassInstances ? *pNumClassInstances : 0)))) { proxy_output_dispose(&wire_ppVertexShader,SD_COM_IF_ID3D11VertexShader); proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[1] = guest_address(wire_ppClassInstances.tokens);
    packet.args[2] = guest_address(pNumClassInstances);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppVertexShader,ppVertexShader,safe_array_count(1),SD_COM_IF_ID3D11VertexShader)) status=E_OUTOFMEMORY;
    if (status >= 0 && !proxy_output_publish(&wire_ppClassInstances,ppClassInstances,safe_array_count((pNumClassInstances ? *pNumClassInstances : 0)),SD_COM_IF_ID3D11ClassInstance)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppVertexShader,ppVertexShader);
    proxy_output_dispose(&wire_ppVertexShader,SD_COM_IF_ID3D11VertexShader);
    if (!(status >= 0)) proxy_output_retract(&wire_ppClassInstances,ppClassInstances);
    proxy_output_dispose(&wire_ppClassInstances,SD_COM_IF_ID3D11ClassInstance);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_PSGetConstantBuffers(ID3D11DeviceContext *This, UINT StartSlot, UINT NumBuffers, ID3D11Buffer ** ppConstantBuffers) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 77};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumBuffers;
    struct proxy_output wire_ppConstantBuffers;
    if (!proxy_output_init(&wire_ppConstantBuffers,ppConstantBuffers,safe_array_count(NumBuffers))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[2] = guest_address(wire_ppConstantBuffers.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppConstantBuffers,ppConstantBuffers,safe_array_count(NumBuffers),SD_COM_IF_ID3D11Buffer)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppConstantBuffers,ppConstantBuffers);
    proxy_output_dispose(&wire_ppConstantBuffers,SD_COM_IF_ID3D11Buffer);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_IAGetInputLayout(ID3D11DeviceContext *This, ID3D11InputLayout ** ppInputLayout) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 78};
    struct proxy_output wire_ppInputLayout;
    if (!proxy_output_init(&wire_ppInputLayout,ppInputLayout,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppInputLayout.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppInputLayout,ppInputLayout,safe_array_count(1),SD_COM_IF_ID3D11InputLayout)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppInputLayout,ppInputLayout);
    proxy_output_dispose(&wire_ppInputLayout,SD_COM_IF_ID3D11InputLayout);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_IAGetVertexBuffers(ID3D11DeviceContext *This, UINT StartSlot, UINT NumBuffers, ID3D11Buffer ** ppVertexBuffers, UINT * pStrides, UINT * pOffsets) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 79};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumBuffers;
    struct proxy_output wire_ppVertexBuffers;
    if (!proxy_output_init(&wire_ppVertexBuffers,ppVertexBuffers,safe_array_count(NumBuffers))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[2] = guest_address(wire_ppVertexBuffers.tokens);
    packet.args[3] = guest_address(pStrides);
    packet.args[4] = guest_address(pOffsets);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppVertexBuffers,ppVertexBuffers,safe_array_count(NumBuffers),SD_COM_IF_ID3D11Buffer)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppVertexBuffers,ppVertexBuffers);
    proxy_output_dispose(&wire_ppVertexBuffers,SD_COM_IF_ID3D11Buffer);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_IAGetIndexBuffer(ID3D11DeviceContext *This, ID3D11Buffer ** pIndexBuffer, DXGI_FORMAT * Format, UINT * Offset) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 80};
    struct proxy_output wire_pIndexBuffer;
    if (!proxy_output_init(&wire_pIndexBuffer,pIndexBuffer,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_pIndexBuffer.tokens);
    packet.args[1] = guest_address(Format);
    packet.args[2] = guest_address(Offset);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_pIndexBuffer,pIndexBuffer,safe_array_count(1),SD_COM_IF_ID3D11Buffer)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_pIndexBuffer,pIndexBuffer);
    proxy_output_dispose(&wire_pIndexBuffer,SD_COM_IF_ID3D11Buffer);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_GSGetConstantBuffers(ID3D11DeviceContext *This, UINT StartSlot, UINT NumBuffers, ID3D11Buffer ** ppConstantBuffers) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 81};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumBuffers;
    struct proxy_output wire_ppConstantBuffers;
    if (!proxy_output_init(&wire_ppConstantBuffers,ppConstantBuffers,safe_array_count(NumBuffers))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[2] = guest_address(wire_ppConstantBuffers.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppConstantBuffers,ppConstantBuffers,safe_array_count(NumBuffers),SD_COM_IF_ID3D11Buffer)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppConstantBuffers,ppConstantBuffers);
    proxy_output_dispose(&wire_ppConstantBuffers,SD_COM_IF_ID3D11Buffer);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_GSGetShader(ID3D11DeviceContext *This, ID3D11GeometryShader ** ppGeometryShader, ID3D11ClassInstance ** ppClassInstances, UINT * pNumClassInstances) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 82};
    struct proxy_output wire_ppGeometryShader;
    if (!proxy_output_init(&wire_ppGeometryShader,ppGeometryShader,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppGeometryShader.tokens);
    struct proxy_output wire_ppClassInstances;
    if (!proxy_output_init(&wire_ppClassInstances,ppClassInstances,safe_array_count((pNumClassInstances ? *pNumClassInstances : 0)))) { proxy_output_dispose(&wire_ppGeometryShader,SD_COM_IF_ID3D11GeometryShader); proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[1] = guest_address(wire_ppClassInstances.tokens);
    packet.args[2] = guest_address(pNumClassInstances);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppGeometryShader,ppGeometryShader,safe_array_count(1),SD_COM_IF_ID3D11GeometryShader)) status=E_OUTOFMEMORY;
    if (status >= 0 && !proxy_output_publish(&wire_ppClassInstances,ppClassInstances,safe_array_count((pNumClassInstances ? *pNumClassInstances : 0)),SD_COM_IF_ID3D11ClassInstance)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppGeometryShader,ppGeometryShader);
    proxy_output_dispose(&wire_ppGeometryShader,SD_COM_IF_ID3D11GeometryShader);
    if (!(status >= 0)) proxy_output_retract(&wire_ppClassInstances,ppClassInstances);
    proxy_output_dispose(&wire_ppClassInstances,SD_COM_IF_ID3D11ClassInstance);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_IAGetPrimitiveTopology(ID3D11DeviceContext *This, D3D11_PRIMITIVE_TOPOLOGY * pTopology) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 83};
    packet.args[0] = guest_address(pTopology);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_VSGetShaderResources(ID3D11DeviceContext *This, UINT StartSlot, UINT NumViews, ID3D11ShaderResourceView ** ppShaderResourceViews) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 84};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumViews;
    struct proxy_output wire_ppShaderResourceViews;
    if (!proxy_output_init(&wire_ppShaderResourceViews,ppShaderResourceViews,safe_array_count(NumViews))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[2] = guest_address(wire_ppShaderResourceViews.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppShaderResourceViews,ppShaderResourceViews,safe_array_count(NumViews),SD_COM_IF_ID3D11ShaderResourceView)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppShaderResourceViews,ppShaderResourceViews);
    proxy_output_dispose(&wire_ppShaderResourceViews,SD_COM_IF_ID3D11ShaderResourceView);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_VSGetSamplers(ID3D11DeviceContext *This, UINT StartSlot, UINT NumSamplers, ID3D11SamplerState ** ppSamplers) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 85};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumSamplers;
    struct proxy_output wire_ppSamplers;
    if (!proxy_output_init(&wire_ppSamplers,ppSamplers,safe_array_count(NumSamplers))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[2] = guest_address(wire_ppSamplers.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppSamplers,ppSamplers,safe_array_count(NumSamplers),SD_COM_IF_ID3D11SamplerState)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppSamplers,ppSamplers);
    proxy_output_dispose(&wire_ppSamplers,SD_COM_IF_ID3D11SamplerState);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_GetPredication(ID3D11DeviceContext *This, ID3D11Predicate ** ppPredicate, WINBOOL * pPredicateValue) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 86};
    struct proxy_output wire_ppPredicate;
    if (!proxy_output_init(&wire_ppPredicate,ppPredicate,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppPredicate.tokens);
    packet.args[1] = guest_address(pPredicateValue);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppPredicate,ppPredicate,safe_array_count(1),SD_COM_IF_ID3D11Predicate)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppPredicate,ppPredicate);
    proxy_output_dispose(&wire_ppPredicate,SD_COM_IF_ID3D11Predicate);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_GSGetShaderResources(ID3D11DeviceContext *This, UINT StartSlot, UINT NumViews, ID3D11ShaderResourceView ** ppShaderResourceViews) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 87};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumViews;
    struct proxy_output wire_ppShaderResourceViews;
    if (!proxy_output_init(&wire_ppShaderResourceViews,ppShaderResourceViews,safe_array_count(NumViews))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[2] = guest_address(wire_ppShaderResourceViews.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppShaderResourceViews,ppShaderResourceViews,safe_array_count(NumViews),SD_COM_IF_ID3D11ShaderResourceView)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppShaderResourceViews,ppShaderResourceViews);
    proxy_output_dispose(&wire_ppShaderResourceViews,SD_COM_IF_ID3D11ShaderResourceView);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_GSGetSamplers(ID3D11DeviceContext *This, UINT StartSlot, UINT NumSamplers, ID3D11SamplerState ** ppSamplers) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 88};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumSamplers;
    struct proxy_output wire_ppSamplers;
    if (!proxy_output_init(&wire_ppSamplers,ppSamplers,safe_array_count(NumSamplers))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[2] = guest_address(wire_ppSamplers.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppSamplers,ppSamplers,safe_array_count(NumSamplers),SD_COM_IF_ID3D11SamplerState)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppSamplers,ppSamplers);
    proxy_output_dispose(&wire_ppSamplers,SD_COM_IF_ID3D11SamplerState);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_OMGetRenderTargets(ID3D11DeviceContext *This, UINT NumViews, ID3D11RenderTargetView ** ppRenderTargetViews, ID3D11DepthStencilView ** ppDepthStencilView) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 89};
    packet.args[0] = (uint32_t)NumViews;
    struct proxy_output wire_ppRenderTargetViews;
    if (!proxy_output_init(&wire_ppRenderTargetViews,ppRenderTargetViews,safe_array_count(NumViews))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[1] = guest_address(wire_ppRenderTargetViews.tokens);
    struct proxy_output wire_ppDepthStencilView;
    if (!proxy_output_init(&wire_ppDepthStencilView,ppDepthStencilView,safe_array_count(1))) { proxy_output_dispose(&wire_ppRenderTargetViews,SD_COM_IF_ID3D11RenderTargetView); proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[2] = guest_address(wire_ppDepthStencilView.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppRenderTargetViews,ppRenderTargetViews,safe_array_count(NumViews),SD_COM_IF_ID3D11RenderTargetView)) status=E_OUTOFMEMORY;
    if (status >= 0 && !proxy_output_publish(&wire_ppDepthStencilView,ppDepthStencilView,safe_array_count(1),SD_COM_IF_ID3D11DepthStencilView)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppRenderTargetViews,ppRenderTargetViews);
    proxy_output_dispose(&wire_ppRenderTargetViews,SD_COM_IF_ID3D11RenderTargetView);
    if (!(status >= 0)) proxy_output_retract(&wire_ppDepthStencilView,ppDepthStencilView);
    proxy_output_dispose(&wire_ppDepthStencilView,SD_COM_IF_ID3D11DepthStencilView);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_OMGetRenderTargetsAndUnorderedAccessViews(ID3D11DeviceContext *This, UINT NumRTVs, ID3D11RenderTargetView ** ppRenderTargetViews, ID3D11DepthStencilView ** ppDepthStencilView, UINT UAVStartSlot, UINT NumUAVs, ID3D11UnorderedAccessView ** ppUnorderedAccessViews) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 90};
    packet.args[0] = (uint32_t)NumRTVs;
    struct proxy_output wire_ppRenderTargetViews;
    if (!proxy_output_init(&wire_ppRenderTargetViews,ppRenderTargetViews,safe_array_count(NumRTVs))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[1] = guest_address(wire_ppRenderTargetViews.tokens);
    struct proxy_output wire_ppDepthStencilView;
    if (!proxy_output_init(&wire_ppDepthStencilView,ppDepthStencilView,safe_array_count(1))) { proxy_output_dispose(&wire_ppRenderTargetViews,SD_COM_IF_ID3D11RenderTargetView); proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[2] = guest_address(wire_ppDepthStencilView.tokens);
    packet.args[3] = (uint32_t)UAVStartSlot;
    packet.args[4] = (uint32_t)NumUAVs;
    struct proxy_output wire_ppUnorderedAccessViews;
    if (!proxy_output_init(&wire_ppUnorderedAccessViews,ppUnorderedAccessViews,safe_array_count(NumUAVs))) { proxy_output_dispose(&wire_ppRenderTargetViews,SD_COM_IF_ID3D11RenderTargetView); proxy_output_dispose(&wire_ppDepthStencilView,SD_COM_IF_ID3D11DepthStencilView); proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[5] = guest_address(wire_ppUnorderedAccessViews.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppRenderTargetViews,ppRenderTargetViews,safe_array_count(NumRTVs),SD_COM_IF_ID3D11RenderTargetView)) status=E_OUTOFMEMORY;
    if (status >= 0 && !proxy_output_publish(&wire_ppDepthStencilView,ppDepthStencilView,safe_array_count(1),SD_COM_IF_ID3D11DepthStencilView)) status=E_OUTOFMEMORY;
    if (status >= 0 && !proxy_output_publish(&wire_ppUnorderedAccessViews,ppUnorderedAccessViews,safe_array_count(NumUAVs),SD_COM_IF_ID3D11UnorderedAccessView)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppRenderTargetViews,ppRenderTargetViews);
    proxy_output_dispose(&wire_ppRenderTargetViews,SD_COM_IF_ID3D11RenderTargetView);
    if (!(status >= 0)) proxy_output_retract(&wire_ppDepthStencilView,ppDepthStencilView);
    proxy_output_dispose(&wire_ppDepthStencilView,SD_COM_IF_ID3D11DepthStencilView);
    if (!(status >= 0)) proxy_output_retract(&wire_ppUnorderedAccessViews,ppUnorderedAccessViews);
    proxy_output_dispose(&wire_ppUnorderedAccessViews,SD_COM_IF_ID3D11UnorderedAccessView);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_OMGetBlendState(ID3D11DeviceContext *This, ID3D11BlendState ** ppBlendState, FLOAT BlendFactor[4], UINT * pSampleMask) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 91};
    struct proxy_output wire_ppBlendState;
    if (!proxy_output_init(&wire_ppBlendState,ppBlendState,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppBlendState.tokens);
    packet.args[1] = guest_address(BlendFactor);
    packet.args[2] = guest_address(pSampleMask);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppBlendState,ppBlendState,safe_array_count(1),SD_COM_IF_ID3D11BlendState)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppBlendState,ppBlendState);
    proxy_output_dispose(&wire_ppBlendState,SD_COM_IF_ID3D11BlendState);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_OMGetDepthStencilState(ID3D11DeviceContext *This, ID3D11DepthStencilState ** ppDepthStencilState, UINT * pStencilRef) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 92};
    struct proxy_output wire_ppDepthStencilState;
    if (!proxy_output_init(&wire_ppDepthStencilState,ppDepthStencilState,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDepthStencilState.tokens);
    packet.args[1] = guest_address(pStencilRef);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDepthStencilState,ppDepthStencilState,safe_array_count(1),SD_COM_IF_ID3D11DepthStencilState)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDepthStencilState,ppDepthStencilState);
    proxy_output_dispose(&wire_ppDepthStencilState,SD_COM_IF_ID3D11DepthStencilState);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_SOGetTargets(ID3D11DeviceContext *This, UINT NumBuffers, ID3D11Buffer ** ppSOTargets) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 93};
    packet.args[0] = (uint32_t)NumBuffers;
    struct proxy_output wire_ppSOTargets;
    if (!proxy_output_init(&wire_ppSOTargets,ppSOTargets,safe_array_count(NumBuffers))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[1] = guest_address(wire_ppSOTargets.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppSOTargets,ppSOTargets,safe_array_count(NumBuffers),SD_COM_IF_ID3D11Buffer)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppSOTargets,ppSOTargets);
    proxy_output_dispose(&wire_ppSOTargets,SD_COM_IF_ID3D11Buffer);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_RSGetState(ID3D11DeviceContext *This, ID3D11RasterizerState ** ppRasterizerState) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 94};
    struct proxy_output wire_ppRasterizerState;
    if (!proxy_output_init(&wire_ppRasterizerState,ppRasterizerState,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppRasterizerState.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppRasterizerState,ppRasterizerState,safe_array_count(1),SD_COM_IF_ID3D11RasterizerState)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppRasterizerState,ppRasterizerState);
    proxy_output_dispose(&wire_ppRasterizerState,SD_COM_IF_ID3D11RasterizerState);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_RSGetViewports(ID3D11DeviceContext *This, UINT * pNumViewports, D3D11_VIEWPORT * pViewports) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 95};
    packet.args[0] = guest_address(pNumViewports);
    packet.args[1] = guest_address(pViewports);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_RSGetScissorRects(ID3D11DeviceContext *This, UINT * pNumRects, D3D11_RECT * pRects) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 96};
    packet.args[0] = guest_address(pNumRects);
    packet.args[1] = guest_address(pRects);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_HSGetShaderResources(ID3D11DeviceContext *This, UINT StartSlot, UINT NumViews, ID3D11ShaderResourceView ** ppShaderResourceViews) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 97};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumViews;
    struct proxy_output wire_ppShaderResourceViews;
    if (!proxy_output_init(&wire_ppShaderResourceViews,ppShaderResourceViews,safe_array_count(NumViews))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[2] = guest_address(wire_ppShaderResourceViews.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppShaderResourceViews,ppShaderResourceViews,safe_array_count(NumViews),SD_COM_IF_ID3D11ShaderResourceView)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppShaderResourceViews,ppShaderResourceViews);
    proxy_output_dispose(&wire_ppShaderResourceViews,SD_COM_IF_ID3D11ShaderResourceView);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_HSGetShader(ID3D11DeviceContext *This, ID3D11HullShader ** ppHullShader, ID3D11ClassInstance ** ppClassInstances, UINT * pNumClassInstances) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 98};
    struct proxy_output wire_ppHullShader;
    if (!proxy_output_init(&wire_ppHullShader,ppHullShader,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppHullShader.tokens);
    struct proxy_output wire_ppClassInstances;
    if (!proxy_output_init(&wire_ppClassInstances,ppClassInstances,safe_array_count((pNumClassInstances ? *pNumClassInstances : 0)))) { proxy_output_dispose(&wire_ppHullShader,SD_COM_IF_ID3D11HullShader); proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[1] = guest_address(wire_ppClassInstances.tokens);
    packet.args[2] = guest_address(pNumClassInstances);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppHullShader,ppHullShader,safe_array_count(1),SD_COM_IF_ID3D11HullShader)) status=E_OUTOFMEMORY;
    if (status >= 0 && !proxy_output_publish(&wire_ppClassInstances,ppClassInstances,safe_array_count((pNumClassInstances ? *pNumClassInstances : 0)),SD_COM_IF_ID3D11ClassInstance)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppHullShader,ppHullShader);
    proxy_output_dispose(&wire_ppHullShader,SD_COM_IF_ID3D11HullShader);
    if (!(status >= 0)) proxy_output_retract(&wire_ppClassInstances,ppClassInstances);
    proxy_output_dispose(&wire_ppClassInstances,SD_COM_IF_ID3D11ClassInstance);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_HSGetSamplers(ID3D11DeviceContext *This, UINT StartSlot, UINT NumSamplers, ID3D11SamplerState ** ppSamplers) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 99};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumSamplers;
    struct proxy_output wire_ppSamplers;
    if (!proxy_output_init(&wire_ppSamplers,ppSamplers,safe_array_count(NumSamplers))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[2] = guest_address(wire_ppSamplers.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppSamplers,ppSamplers,safe_array_count(NumSamplers),SD_COM_IF_ID3D11SamplerState)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppSamplers,ppSamplers);
    proxy_output_dispose(&wire_ppSamplers,SD_COM_IF_ID3D11SamplerState);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_HSGetConstantBuffers(ID3D11DeviceContext *This, UINT StartSlot, UINT NumBuffers, ID3D11Buffer ** ppConstantBuffers) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 100};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumBuffers;
    struct proxy_output wire_ppConstantBuffers;
    if (!proxy_output_init(&wire_ppConstantBuffers,ppConstantBuffers,safe_array_count(NumBuffers))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[2] = guest_address(wire_ppConstantBuffers.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppConstantBuffers,ppConstantBuffers,safe_array_count(NumBuffers),SD_COM_IF_ID3D11Buffer)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppConstantBuffers,ppConstantBuffers);
    proxy_output_dispose(&wire_ppConstantBuffers,SD_COM_IF_ID3D11Buffer);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_DSGetShaderResources(ID3D11DeviceContext *This, UINT StartSlot, UINT NumViews, ID3D11ShaderResourceView ** ppShaderResourceViews) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 101};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumViews;
    struct proxy_output wire_ppShaderResourceViews;
    if (!proxy_output_init(&wire_ppShaderResourceViews,ppShaderResourceViews,safe_array_count(NumViews))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[2] = guest_address(wire_ppShaderResourceViews.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppShaderResourceViews,ppShaderResourceViews,safe_array_count(NumViews),SD_COM_IF_ID3D11ShaderResourceView)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppShaderResourceViews,ppShaderResourceViews);
    proxy_output_dispose(&wire_ppShaderResourceViews,SD_COM_IF_ID3D11ShaderResourceView);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_DSGetShader(ID3D11DeviceContext *This, ID3D11DomainShader ** ppDomainShader, ID3D11ClassInstance ** ppClassInstances, UINT * pNumClassInstances) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 102};
    struct proxy_output wire_ppDomainShader;
    if (!proxy_output_init(&wire_ppDomainShader,ppDomainShader,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDomainShader.tokens);
    struct proxy_output wire_ppClassInstances;
    if (!proxy_output_init(&wire_ppClassInstances,ppClassInstances,safe_array_count((pNumClassInstances ? *pNumClassInstances : 0)))) { proxy_output_dispose(&wire_ppDomainShader,SD_COM_IF_ID3D11DomainShader); proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[1] = guest_address(wire_ppClassInstances.tokens);
    packet.args[2] = guest_address(pNumClassInstances);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDomainShader,ppDomainShader,safe_array_count(1),SD_COM_IF_ID3D11DomainShader)) status=E_OUTOFMEMORY;
    if (status >= 0 && !proxy_output_publish(&wire_ppClassInstances,ppClassInstances,safe_array_count((pNumClassInstances ? *pNumClassInstances : 0)),SD_COM_IF_ID3D11ClassInstance)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDomainShader,ppDomainShader);
    proxy_output_dispose(&wire_ppDomainShader,SD_COM_IF_ID3D11DomainShader);
    if (!(status >= 0)) proxy_output_retract(&wire_ppClassInstances,ppClassInstances);
    proxy_output_dispose(&wire_ppClassInstances,SD_COM_IF_ID3D11ClassInstance);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_DSGetSamplers(ID3D11DeviceContext *This, UINT StartSlot, UINT NumSamplers, ID3D11SamplerState ** ppSamplers) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 103};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumSamplers;
    struct proxy_output wire_ppSamplers;
    if (!proxy_output_init(&wire_ppSamplers,ppSamplers,safe_array_count(NumSamplers))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[2] = guest_address(wire_ppSamplers.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppSamplers,ppSamplers,safe_array_count(NumSamplers),SD_COM_IF_ID3D11SamplerState)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppSamplers,ppSamplers);
    proxy_output_dispose(&wire_ppSamplers,SD_COM_IF_ID3D11SamplerState);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_DSGetConstantBuffers(ID3D11DeviceContext *This, UINT StartSlot, UINT NumBuffers, ID3D11Buffer ** ppConstantBuffers) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 104};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumBuffers;
    struct proxy_output wire_ppConstantBuffers;
    if (!proxy_output_init(&wire_ppConstantBuffers,ppConstantBuffers,safe_array_count(NumBuffers))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[2] = guest_address(wire_ppConstantBuffers.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppConstantBuffers,ppConstantBuffers,safe_array_count(NumBuffers),SD_COM_IF_ID3D11Buffer)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppConstantBuffers,ppConstantBuffers);
    proxy_output_dispose(&wire_ppConstantBuffers,SD_COM_IF_ID3D11Buffer);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_CSGetShaderResources(ID3D11DeviceContext *This, UINT StartSlot, UINT NumViews, ID3D11ShaderResourceView ** ppShaderResourceViews) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 105};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumViews;
    struct proxy_output wire_ppShaderResourceViews;
    if (!proxy_output_init(&wire_ppShaderResourceViews,ppShaderResourceViews,safe_array_count(NumViews))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[2] = guest_address(wire_ppShaderResourceViews.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppShaderResourceViews,ppShaderResourceViews,safe_array_count(NumViews),SD_COM_IF_ID3D11ShaderResourceView)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppShaderResourceViews,ppShaderResourceViews);
    proxy_output_dispose(&wire_ppShaderResourceViews,SD_COM_IF_ID3D11ShaderResourceView);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_CSGetUnorderedAccessViews(ID3D11DeviceContext *This, UINT StartSlot, UINT NumUAVs, ID3D11UnorderedAccessView ** ppUnorderedAccessViews) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 106};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumUAVs;
    struct proxy_output wire_ppUnorderedAccessViews;
    if (!proxy_output_init(&wire_ppUnorderedAccessViews,ppUnorderedAccessViews,safe_array_count(NumUAVs))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[2] = guest_address(wire_ppUnorderedAccessViews.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppUnorderedAccessViews,ppUnorderedAccessViews,safe_array_count(NumUAVs),SD_COM_IF_ID3D11UnorderedAccessView)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppUnorderedAccessViews,ppUnorderedAccessViews);
    proxy_output_dispose(&wire_ppUnorderedAccessViews,SD_COM_IF_ID3D11UnorderedAccessView);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_CSGetShader(ID3D11DeviceContext *This, ID3D11ComputeShader ** ppComputeShader, ID3D11ClassInstance ** ppClassInstances, UINT * pNumClassInstances) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 107};
    struct proxy_output wire_ppComputeShader;
    if (!proxy_output_init(&wire_ppComputeShader,ppComputeShader,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppComputeShader.tokens);
    struct proxy_output wire_ppClassInstances;
    if (!proxy_output_init(&wire_ppClassInstances,ppClassInstances,safe_array_count((pNumClassInstances ? *pNumClassInstances : 0)))) { proxy_output_dispose(&wire_ppComputeShader,SD_COM_IF_ID3D11ComputeShader); proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[1] = guest_address(wire_ppClassInstances.tokens);
    packet.args[2] = guest_address(pNumClassInstances);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppComputeShader,ppComputeShader,safe_array_count(1),SD_COM_IF_ID3D11ComputeShader)) status=E_OUTOFMEMORY;
    if (status >= 0 && !proxy_output_publish(&wire_ppClassInstances,ppClassInstances,safe_array_count((pNumClassInstances ? *pNumClassInstances : 0)),SD_COM_IF_ID3D11ClassInstance)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppComputeShader,ppComputeShader);
    proxy_output_dispose(&wire_ppComputeShader,SD_COM_IF_ID3D11ComputeShader);
    if (!(status >= 0)) proxy_output_retract(&wire_ppClassInstances,ppClassInstances);
    proxy_output_dispose(&wire_ppClassInstances,SD_COM_IF_ID3D11ClassInstance);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_CSGetSamplers(ID3D11DeviceContext *This, UINT StartSlot, UINT NumSamplers, ID3D11SamplerState ** ppSamplers) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 108};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumSamplers;
    struct proxy_output wire_ppSamplers;
    if (!proxy_output_init(&wire_ppSamplers,ppSamplers,safe_array_count(NumSamplers))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[2] = guest_address(wire_ppSamplers.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppSamplers,ppSamplers,safe_array_count(NumSamplers),SD_COM_IF_ID3D11SamplerState)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppSamplers,ppSamplers);
    proxy_output_dispose(&wire_ppSamplers,SD_COM_IF_ID3D11SamplerState);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_CSGetConstantBuffers(ID3D11DeviceContext *This, UINT StartSlot, UINT NumBuffers, ID3D11Buffer ** ppConstantBuffers) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 109};
    packet.args[0] = (uint32_t)StartSlot;
    packet.args[1] = (uint32_t)NumBuffers;
    struct proxy_output wire_ppConstantBuffers;
    if (!proxy_output_init(&wire_ppConstantBuffers,ppConstantBuffers,safe_array_count(NumBuffers))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[2] = guest_address(wire_ppConstantBuffers.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppConstantBuffers,ppConstantBuffers,safe_array_count(NumBuffers),SD_COM_IF_ID3D11Buffer)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppConstantBuffers,ppConstantBuffers);
    proxy_output_dispose(&wire_ppConstantBuffers,SD_COM_IF_ID3D11Buffer);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_ClearState(ID3D11DeviceContext *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 110};
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11DeviceContext_Flush(ID3D11DeviceContext *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 111};
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static D3D11_DEVICE_CONTEXT_TYPE STDMETHODCALLTYPE g_ID3D11DeviceContext_GetType(ID3D11DeviceContext *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 112};
    LONG status = proxy_call(&packet);
    if (status < 0) { return (D3D11_DEVICE_CONTEXT_TYPE)status; }
    return (D3D11_DEVICE_CONTEXT_TYPE)packet.ret;
}
static UINT STDMETHODCALLTYPE g_ID3D11DeviceContext_GetContextFlags(ID3D11DeviceContext *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 113};
    LONG status = proxy_call(&packet);
    if (status < 0) { return (UINT)status; }
    return (UINT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11DeviceContext_FinishCommandList(ID3D11DeviceContext *This, WINBOOL RestoreDeferredContextState, ID3D11CommandList ** ppCommandList) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DeviceContext, 114};
    packet.args[0] = (uint32_t)RestoreDeferredContextState;
    struct proxy_output wire_ppCommandList;
    if (!proxy_output_init(&wire_ppCommandList,ppCommandList,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_ppCommandList.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppCommandList,ppCommandList,safe_array_count(1),SD_COM_IF_ID3D11CommandList)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppCommandList,ppCommandList);
    proxy_output_dispose(&wire_ppCommandList,SD_COM_IF_ID3D11CommandList);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static const ID3D11DeviceContextVtbl vtbl_ID3D11DeviceContext = {
    g_ID3D11DeviceContext_QueryInterface,
    g_ID3D11DeviceContext_AddRef,
    g_ID3D11DeviceContext_Release,
    g_ID3D11DeviceContext_GetDevice,
    g_ID3D11DeviceContext_GetPrivateData,
    g_ID3D11DeviceContext_SetPrivateData,
    g_ID3D11DeviceContext_SetPrivateDataInterface,
    g_ID3D11DeviceContext_VSSetConstantBuffers,
    g_ID3D11DeviceContext_PSSetShaderResources,
    g_ID3D11DeviceContext_PSSetShader,
    g_ID3D11DeviceContext_PSSetSamplers,
    g_ID3D11DeviceContext_VSSetShader,
    g_ID3D11DeviceContext_DrawIndexed,
    g_ID3D11DeviceContext_Draw,
    g_ID3D11DeviceContext_Map,
    g_ID3D11DeviceContext_Unmap,
    g_ID3D11DeviceContext_PSSetConstantBuffers,
    g_ID3D11DeviceContext_IASetInputLayout,
    g_ID3D11DeviceContext_IASetVertexBuffers,
    g_ID3D11DeviceContext_IASetIndexBuffer,
    g_ID3D11DeviceContext_DrawIndexedInstanced,
    g_ID3D11DeviceContext_DrawInstanced,
    g_ID3D11DeviceContext_GSSetConstantBuffers,
    g_ID3D11DeviceContext_GSSetShader,
    g_ID3D11DeviceContext_IASetPrimitiveTopology,
    g_ID3D11DeviceContext_VSSetShaderResources,
    g_ID3D11DeviceContext_VSSetSamplers,
    g_ID3D11DeviceContext_Begin,
    g_ID3D11DeviceContext_End,
    g_ID3D11DeviceContext_GetData,
    g_ID3D11DeviceContext_SetPredication,
    g_ID3D11DeviceContext_GSSetShaderResources,
    g_ID3D11DeviceContext_GSSetSamplers,
    g_ID3D11DeviceContext_OMSetRenderTargets,
    g_ID3D11DeviceContext_OMSetRenderTargetsAndUnorderedAccessViews,
    g_ID3D11DeviceContext_OMSetBlendState,
    g_ID3D11DeviceContext_OMSetDepthStencilState,
    g_ID3D11DeviceContext_SOSetTargets,
    g_ID3D11DeviceContext_DrawAuto,
    g_ID3D11DeviceContext_DrawIndexedInstancedIndirect,
    g_ID3D11DeviceContext_DrawInstancedIndirect,
    g_ID3D11DeviceContext_Dispatch,
    g_ID3D11DeviceContext_DispatchIndirect,
    g_ID3D11DeviceContext_RSSetState,
    g_ID3D11DeviceContext_RSSetViewports,
    g_ID3D11DeviceContext_RSSetScissorRects,
    g_ID3D11DeviceContext_CopySubresourceRegion,
    g_ID3D11DeviceContext_CopyResource,
    g_ID3D11DeviceContext_UpdateSubresource,
    g_ID3D11DeviceContext_CopyStructureCount,
    g_ID3D11DeviceContext_ClearRenderTargetView,
    g_ID3D11DeviceContext_ClearUnorderedAccessViewUint,
    g_ID3D11DeviceContext_ClearUnorderedAccessViewFloat,
    g_ID3D11DeviceContext_ClearDepthStencilView,
    g_ID3D11DeviceContext_GenerateMips,
    g_ID3D11DeviceContext_SetResourceMinLOD,
    g_ID3D11DeviceContext_GetResourceMinLOD,
    g_ID3D11DeviceContext_ResolveSubresource,
    g_ID3D11DeviceContext_ExecuteCommandList,
    g_ID3D11DeviceContext_HSSetShaderResources,
    g_ID3D11DeviceContext_HSSetShader,
    g_ID3D11DeviceContext_HSSetSamplers,
    g_ID3D11DeviceContext_HSSetConstantBuffers,
    g_ID3D11DeviceContext_DSSetShaderResources,
    g_ID3D11DeviceContext_DSSetShader,
    g_ID3D11DeviceContext_DSSetSamplers,
    g_ID3D11DeviceContext_DSSetConstantBuffers,
    g_ID3D11DeviceContext_CSSetShaderResources,
    g_ID3D11DeviceContext_CSSetUnorderedAccessViews,
    g_ID3D11DeviceContext_CSSetShader,
    g_ID3D11DeviceContext_CSSetSamplers,
    g_ID3D11DeviceContext_CSSetConstantBuffers,
    g_ID3D11DeviceContext_VSGetConstantBuffers,
    g_ID3D11DeviceContext_PSGetShaderResources,
    g_ID3D11DeviceContext_PSGetShader,
    g_ID3D11DeviceContext_PSGetSamplers,
    g_ID3D11DeviceContext_VSGetShader,
    g_ID3D11DeviceContext_PSGetConstantBuffers,
    g_ID3D11DeviceContext_IAGetInputLayout,
    g_ID3D11DeviceContext_IAGetVertexBuffers,
    g_ID3D11DeviceContext_IAGetIndexBuffer,
    g_ID3D11DeviceContext_GSGetConstantBuffers,
    g_ID3D11DeviceContext_GSGetShader,
    g_ID3D11DeviceContext_IAGetPrimitiveTopology,
    g_ID3D11DeviceContext_VSGetShaderResources,
    g_ID3D11DeviceContext_VSGetSamplers,
    g_ID3D11DeviceContext_GetPredication,
    g_ID3D11DeviceContext_GSGetShaderResources,
    g_ID3D11DeviceContext_GSGetSamplers,
    g_ID3D11DeviceContext_OMGetRenderTargets,
    g_ID3D11DeviceContext_OMGetRenderTargetsAndUnorderedAccessViews,
    g_ID3D11DeviceContext_OMGetBlendState,
    g_ID3D11DeviceContext_OMGetDepthStencilState,
    g_ID3D11DeviceContext_SOGetTargets,
    g_ID3D11DeviceContext_RSGetState,
    g_ID3D11DeviceContext_RSGetViewports,
    g_ID3D11DeviceContext_RSGetScissorRects,
    g_ID3D11DeviceContext_HSGetShaderResources,
    g_ID3D11DeviceContext_HSGetShader,
    g_ID3D11DeviceContext_HSGetSamplers,
    g_ID3D11DeviceContext_HSGetConstantBuffers,
    g_ID3D11DeviceContext_DSGetShaderResources,
    g_ID3D11DeviceContext_DSGetShader,
    g_ID3D11DeviceContext_DSGetSamplers,
    g_ID3D11DeviceContext_DSGetConstantBuffers,
    g_ID3D11DeviceContext_CSGetShaderResources,
    g_ID3D11DeviceContext_CSGetUnorderedAccessViews,
    g_ID3D11DeviceContext_CSGetShader,
    g_ID3D11DeviceContext_CSGetSamplers,
    g_ID3D11DeviceContext_CSGetConstantBuffers,
    g_ID3D11DeviceContext_ClearState,
    g_ID3D11DeviceContext_Flush,
    g_ID3D11DeviceContext_GetType,
    g_ID3D11DeviceContext_GetContextFlags,
    g_ID3D11DeviceContext_FinishCommandList
};
static HRESULT STDMETHODCALLTYPE g_ID3D11DomainShader_QueryInterface(ID3D11DomainShader *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11DomainShader_AddRef(ID3D11DomainShader *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11DomainShader_Release(ID3D11DomainShader *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11DomainShader_GetDevice(ID3D11DomainShader *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DomainShader, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11DomainShader_GetPrivateData(ID3D11DomainShader *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11DomainShader_SetPrivateData(ID3D11DomainShader *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DomainShader, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11DomainShader_SetPrivateDataInterface(ID3D11DomainShader *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11DomainShader, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static const ID3D11DomainShaderVtbl vtbl_ID3D11DomainShader = {
    g_ID3D11DomainShader_QueryInterface,
    g_ID3D11DomainShader_AddRef,
    g_ID3D11DomainShader_Release,
    g_ID3D11DomainShader_GetDevice,
    g_ID3D11DomainShader_GetPrivateData,
    g_ID3D11DomainShader_SetPrivateData,
    g_ID3D11DomainShader_SetPrivateDataInterface
};
static HRESULT STDMETHODCALLTYPE g_ID3D11GeometryShader_QueryInterface(ID3D11GeometryShader *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11GeometryShader_AddRef(ID3D11GeometryShader *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11GeometryShader_Release(ID3D11GeometryShader *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11GeometryShader_GetDevice(ID3D11GeometryShader *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11GeometryShader, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11GeometryShader_GetPrivateData(ID3D11GeometryShader *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11GeometryShader_SetPrivateData(ID3D11GeometryShader *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11GeometryShader, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11GeometryShader_SetPrivateDataInterface(ID3D11GeometryShader *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11GeometryShader, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static const ID3D11GeometryShaderVtbl vtbl_ID3D11GeometryShader = {
    g_ID3D11GeometryShader_QueryInterface,
    g_ID3D11GeometryShader_AddRef,
    g_ID3D11GeometryShader_Release,
    g_ID3D11GeometryShader_GetDevice,
    g_ID3D11GeometryShader_GetPrivateData,
    g_ID3D11GeometryShader_SetPrivateData,
    g_ID3D11GeometryShader_SetPrivateDataInterface
};
static HRESULT STDMETHODCALLTYPE g_ID3D11HullShader_QueryInterface(ID3D11HullShader *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11HullShader_AddRef(ID3D11HullShader *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11HullShader_Release(ID3D11HullShader *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11HullShader_GetDevice(ID3D11HullShader *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11HullShader, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11HullShader_GetPrivateData(ID3D11HullShader *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11HullShader_SetPrivateData(ID3D11HullShader *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11HullShader, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11HullShader_SetPrivateDataInterface(ID3D11HullShader *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11HullShader, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static const ID3D11HullShaderVtbl vtbl_ID3D11HullShader = {
    g_ID3D11HullShader_QueryInterface,
    g_ID3D11HullShader_AddRef,
    g_ID3D11HullShader_Release,
    g_ID3D11HullShader_GetDevice,
    g_ID3D11HullShader_GetPrivateData,
    g_ID3D11HullShader_SetPrivateData,
    g_ID3D11HullShader_SetPrivateDataInterface
};
static HRESULT STDMETHODCALLTYPE g_ID3D11InputLayout_QueryInterface(ID3D11InputLayout *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11InputLayout_AddRef(ID3D11InputLayout *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11InputLayout_Release(ID3D11InputLayout *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11InputLayout_GetDevice(ID3D11InputLayout *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11InputLayout, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11InputLayout_GetPrivateData(ID3D11InputLayout *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11InputLayout_SetPrivateData(ID3D11InputLayout *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11InputLayout, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11InputLayout_SetPrivateDataInterface(ID3D11InputLayout *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11InputLayout, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static const ID3D11InputLayoutVtbl vtbl_ID3D11InputLayout = {
    g_ID3D11InputLayout_QueryInterface,
    g_ID3D11InputLayout_AddRef,
    g_ID3D11InputLayout_Release,
    g_ID3D11InputLayout_GetDevice,
    g_ID3D11InputLayout_GetPrivateData,
    g_ID3D11InputLayout_SetPrivateData,
    g_ID3D11InputLayout_SetPrivateDataInterface
};
static HRESULT STDMETHODCALLTYPE g_ID3D11PixelShader_QueryInterface(ID3D11PixelShader *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11PixelShader_AddRef(ID3D11PixelShader *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11PixelShader_Release(ID3D11PixelShader *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11PixelShader_GetDevice(ID3D11PixelShader *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11PixelShader, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11PixelShader_GetPrivateData(ID3D11PixelShader *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11PixelShader_SetPrivateData(ID3D11PixelShader *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11PixelShader, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11PixelShader_SetPrivateDataInterface(ID3D11PixelShader *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11PixelShader, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static const ID3D11PixelShaderVtbl vtbl_ID3D11PixelShader = {
    g_ID3D11PixelShader_QueryInterface,
    g_ID3D11PixelShader_AddRef,
    g_ID3D11PixelShader_Release,
    g_ID3D11PixelShader_GetDevice,
    g_ID3D11PixelShader_GetPrivateData,
    g_ID3D11PixelShader_SetPrivateData,
    g_ID3D11PixelShader_SetPrivateDataInterface
};
static HRESULT STDMETHODCALLTYPE g_ID3D11Predicate_QueryInterface(ID3D11Predicate *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11Predicate_AddRef(ID3D11Predicate *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11Predicate_Release(ID3D11Predicate *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11Predicate_GetDevice(ID3D11Predicate *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Predicate, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Predicate_GetPrivateData(ID3D11Predicate *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Predicate_SetPrivateData(ID3D11Predicate *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Predicate, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Predicate_SetPrivateDataInterface(ID3D11Predicate *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Predicate, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static UINT STDMETHODCALLTYPE g_ID3D11Predicate_GetDataSize(ID3D11Predicate *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Predicate, 7};
    LONG status = proxy_call(&packet);
    if (status < 0) { return (UINT)status; }
    return (UINT)packet.ret;
}
static void STDMETHODCALLTYPE g_ID3D11Predicate_GetDesc(ID3D11Predicate *This, D3D11_QUERY_DESC * pDesc) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Predicate, 8};
    packet.args[0] = guest_address(pDesc);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static const ID3D11PredicateVtbl vtbl_ID3D11Predicate = {
    g_ID3D11Predicate_QueryInterface,
    g_ID3D11Predicate_AddRef,
    g_ID3D11Predicate_Release,
    g_ID3D11Predicate_GetDevice,
    g_ID3D11Predicate_GetPrivateData,
    g_ID3D11Predicate_SetPrivateData,
    g_ID3D11Predicate_SetPrivateDataInterface,
    g_ID3D11Predicate_GetDataSize,
    g_ID3D11Predicate_GetDesc
};
static HRESULT STDMETHODCALLTYPE g_ID3D11Query_QueryInterface(ID3D11Query *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11Query_AddRef(ID3D11Query *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11Query_Release(ID3D11Query *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11Query_GetDevice(ID3D11Query *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Query, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Query_GetPrivateData(ID3D11Query *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Query_SetPrivateData(ID3D11Query *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Query, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Query_SetPrivateDataInterface(ID3D11Query *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Query, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static UINT STDMETHODCALLTYPE g_ID3D11Query_GetDataSize(ID3D11Query *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Query, 7};
    LONG status = proxy_call(&packet);
    if (status < 0) { return (UINT)status; }
    return (UINT)packet.ret;
}
static void STDMETHODCALLTYPE g_ID3D11Query_GetDesc(ID3D11Query *This, D3D11_QUERY_DESC * pDesc) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Query, 8};
    packet.args[0] = guest_address(pDesc);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static const ID3D11QueryVtbl vtbl_ID3D11Query = {
    g_ID3D11Query_QueryInterface,
    g_ID3D11Query_AddRef,
    g_ID3D11Query_Release,
    g_ID3D11Query_GetDevice,
    g_ID3D11Query_GetPrivateData,
    g_ID3D11Query_SetPrivateData,
    g_ID3D11Query_SetPrivateDataInterface,
    g_ID3D11Query_GetDataSize,
    g_ID3D11Query_GetDesc
};
static HRESULT STDMETHODCALLTYPE g_ID3D11RasterizerState_QueryInterface(ID3D11RasterizerState *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11RasterizerState_AddRef(ID3D11RasterizerState *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11RasterizerState_Release(ID3D11RasterizerState *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11RasterizerState_GetDevice(ID3D11RasterizerState *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11RasterizerState, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11RasterizerState_GetPrivateData(ID3D11RasterizerState *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11RasterizerState_SetPrivateData(ID3D11RasterizerState *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11RasterizerState, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11RasterizerState_SetPrivateDataInterface(ID3D11RasterizerState *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11RasterizerState, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static void STDMETHODCALLTYPE g_ID3D11RasterizerState_GetDesc(ID3D11RasterizerState *This, D3D11_RASTERIZER_DESC * pDesc) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11RasterizerState, 7};
    packet.args[0] = guest_address(pDesc);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static const ID3D11RasterizerStateVtbl vtbl_ID3D11RasterizerState = {
    g_ID3D11RasterizerState_QueryInterface,
    g_ID3D11RasterizerState_AddRef,
    g_ID3D11RasterizerState_Release,
    g_ID3D11RasterizerState_GetDevice,
    g_ID3D11RasterizerState_GetPrivateData,
    g_ID3D11RasterizerState_SetPrivateData,
    g_ID3D11RasterizerState_SetPrivateDataInterface,
    g_ID3D11RasterizerState_GetDesc
};
static HRESULT STDMETHODCALLTYPE g_ID3D11RenderTargetView_QueryInterface(ID3D11RenderTargetView *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11RenderTargetView_AddRef(ID3D11RenderTargetView *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11RenderTargetView_Release(ID3D11RenderTargetView *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11RenderTargetView_GetDevice(ID3D11RenderTargetView *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11RenderTargetView, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11RenderTargetView_GetPrivateData(ID3D11RenderTargetView *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11RenderTargetView_SetPrivateData(ID3D11RenderTargetView *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11RenderTargetView, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11RenderTargetView_SetPrivateDataInterface(ID3D11RenderTargetView *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11RenderTargetView, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static void STDMETHODCALLTYPE g_ID3D11RenderTargetView_GetResource(ID3D11RenderTargetView *This, ID3D11Resource ** ppResource) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11RenderTargetView, 7};
    struct proxy_output wire_ppResource;
    if (!proxy_output_init(&wire_ppResource,ppResource,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppResource.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppResource,ppResource,safe_array_count(1),SD_COM_IF_ID3D11Resource)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppResource,ppResource);
    proxy_output_dispose(&wire_ppResource,SD_COM_IF_ID3D11Resource);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11RenderTargetView_GetDesc(ID3D11RenderTargetView *This, D3D11_RENDER_TARGET_VIEW_DESC * pDesc) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11RenderTargetView, 8};
    packet.args[0] = guest_address(pDesc);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static const ID3D11RenderTargetViewVtbl vtbl_ID3D11RenderTargetView = {
    g_ID3D11RenderTargetView_QueryInterface,
    g_ID3D11RenderTargetView_AddRef,
    g_ID3D11RenderTargetView_Release,
    g_ID3D11RenderTargetView_GetDevice,
    g_ID3D11RenderTargetView_GetPrivateData,
    g_ID3D11RenderTargetView_SetPrivateData,
    g_ID3D11RenderTargetView_SetPrivateDataInterface,
    g_ID3D11RenderTargetView_GetResource,
    g_ID3D11RenderTargetView_GetDesc
};
static HRESULT STDMETHODCALLTYPE g_ID3D11Resource_QueryInterface(ID3D11Resource *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11Resource_AddRef(ID3D11Resource *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11Resource_Release(ID3D11Resource *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11Resource_GetDevice(ID3D11Resource *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Resource, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Resource_GetPrivateData(ID3D11Resource *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Resource_SetPrivateData(ID3D11Resource *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Resource, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Resource_SetPrivateDataInterface(ID3D11Resource *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Resource, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static void STDMETHODCALLTYPE g_ID3D11Resource_GetType(ID3D11Resource *This, D3D11_RESOURCE_DIMENSION * pResourceDimension) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Resource, 7};
    packet.args[0] = guest_address(pResourceDimension);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11Resource_SetEvictionPriority(ID3D11Resource *This, UINT EvictionPriority) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Resource, 8};
    packet.args[0] = (uint32_t)EvictionPriority;
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static UINT STDMETHODCALLTYPE g_ID3D11Resource_GetEvictionPriority(ID3D11Resource *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Resource, 9};
    LONG status = proxy_call(&packet);
    if (status < 0) { return (UINT)status; }
    return (UINT)packet.ret;
}
static const ID3D11ResourceVtbl vtbl_ID3D11Resource = {
    g_ID3D11Resource_QueryInterface,
    g_ID3D11Resource_AddRef,
    g_ID3D11Resource_Release,
    g_ID3D11Resource_GetDevice,
    g_ID3D11Resource_GetPrivateData,
    g_ID3D11Resource_SetPrivateData,
    g_ID3D11Resource_SetPrivateDataInterface,
    g_ID3D11Resource_GetType,
    g_ID3D11Resource_SetEvictionPriority,
    g_ID3D11Resource_GetEvictionPriority
};
static HRESULT STDMETHODCALLTYPE g_ID3D11SamplerState_QueryInterface(ID3D11SamplerState *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11SamplerState_AddRef(ID3D11SamplerState *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11SamplerState_Release(ID3D11SamplerState *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11SamplerState_GetDevice(ID3D11SamplerState *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11SamplerState, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11SamplerState_GetPrivateData(ID3D11SamplerState *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11SamplerState_SetPrivateData(ID3D11SamplerState *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11SamplerState, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11SamplerState_SetPrivateDataInterface(ID3D11SamplerState *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11SamplerState, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static void STDMETHODCALLTYPE g_ID3D11SamplerState_GetDesc(ID3D11SamplerState *This, D3D11_SAMPLER_DESC * pDesc) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11SamplerState, 7};
    packet.args[0] = guest_address(pDesc);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static const ID3D11SamplerStateVtbl vtbl_ID3D11SamplerState = {
    g_ID3D11SamplerState_QueryInterface,
    g_ID3D11SamplerState_AddRef,
    g_ID3D11SamplerState_Release,
    g_ID3D11SamplerState_GetDevice,
    g_ID3D11SamplerState_GetPrivateData,
    g_ID3D11SamplerState_SetPrivateData,
    g_ID3D11SamplerState_SetPrivateDataInterface,
    g_ID3D11SamplerState_GetDesc
};
static HRESULT STDMETHODCALLTYPE g_ID3D11ShaderResourceView_QueryInterface(ID3D11ShaderResourceView *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11ShaderResourceView_AddRef(ID3D11ShaderResourceView *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11ShaderResourceView_Release(ID3D11ShaderResourceView *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11ShaderResourceView_GetDevice(ID3D11ShaderResourceView *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11ShaderResourceView, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11ShaderResourceView_GetPrivateData(ID3D11ShaderResourceView *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11ShaderResourceView_SetPrivateData(ID3D11ShaderResourceView *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11ShaderResourceView, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11ShaderResourceView_SetPrivateDataInterface(ID3D11ShaderResourceView *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11ShaderResourceView, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static void STDMETHODCALLTYPE g_ID3D11ShaderResourceView_GetResource(ID3D11ShaderResourceView *This, ID3D11Resource ** ppResource) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11ShaderResourceView, 7};
    struct proxy_output wire_ppResource;
    if (!proxy_output_init(&wire_ppResource,ppResource,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppResource.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppResource,ppResource,safe_array_count(1),SD_COM_IF_ID3D11Resource)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppResource,ppResource);
    proxy_output_dispose(&wire_ppResource,SD_COM_IF_ID3D11Resource);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11ShaderResourceView_GetDesc(ID3D11ShaderResourceView *This, D3D11_SHADER_RESOURCE_VIEW_DESC * pDesc) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11ShaderResourceView, 8};
    packet.args[0] = guest_address(pDesc);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static const ID3D11ShaderResourceViewVtbl vtbl_ID3D11ShaderResourceView = {
    g_ID3D11ShaderResourceView_QueryInterface,
    g_ID3D11ShaderResourceView_AddRef,
    g_ID3D11ShaderResourceView_Release,
    g_ID3D11ShaderResourceView_GetDevice,
    g_ID3D11ShaderResourceView_GetPrivateData,
    g_ID3D11ShaderResourceView_SetPrivateData,
    g_ID3D11ShaderResourceView_SetPrivateDataInterface,
    g_ID3D11ShaderResourceView_GetResource,
    g_ID3D11ShaderResourceView_GetDesc
};
static HRESULT STDMETHODCALLTYPE g_ID3D11Texture1D_QueryInterface(ID3D11Texture1D *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11Texture1D_AddRef(ID3D11Texture1D *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11Texture1D_Release(ID3D11Texture1D *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11Texture1D_GetDevice(ID3D11Texture1D *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Texture1D, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Texture1D_GetPrivateData(ID3D11Texture1D *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Texture1D_SetPrivateData(ID3D11Texture1D *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Texture1D, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Texture1D_SetPrivateDataInterface(ID3D11Texture1D *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Texture1D, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static void STDMETHODCALLTYPE g_ID3D11Texture1D_GetType(ID3D11Texture1D *This, D3D11_RESOURCE_DIMENSION * pResourceDimension) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Texture1D, 7};
    packet.args[0] = guest_address(pResourceDimension);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11Texture1D_SetEvictionPriority(ID3D11Texture1D *This, UINT EvictionPriority) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Texture1D, 8};
    packet.args[0] = (uint32_t)EvictionPriority;
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static UINT STDMETHODCALLTYPE g_ID3D11Texture1D_GetEvictionPriority(ID3D11Texture1D *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Texture1D, 9};
    LONG status = proxy_call(&packet);
    if (status < 0) { return (UINT)status; }
    return (UINT)packet.ret;
}
static void STDMETHODCALLTYPE g_ID3D11Texture1D_GetDesc(ID3D11Texture1D *This, D3D11_TEXTURE1D_DESC * pDesc) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Texture1D, 10};
    packet.args[0] = guest_address(pDesc);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static const ID3D11Texture1DVtbl vtbl_ID3D11Texture1D = {
    g_ID3D11Texture1D_QueryInterface,
    g_ID3D11Texture1D_AddRef,
    g_ID3D11Texture1D_Release,
    g_ID3D11Texture1D_GetDevice,
    g_ID3D11Texture1D_GetPrivateData,
    g_ID3D11Texture1D_SetPrivateData,
    g_ID3D11Texture1D_SetPrivateDataInterface,
    g_ID3D11Texture1D_GetType,
    g_ID3D11Texture1D_SetEvictionPriority,
    g_ID3D11Texture1D_GetEvictionPriority,
    g_ID3D11Texture1D_GetDesc
};
static HRESULT STDMETHODCALLTYPE g_ID3D11Texture2D_QueryInterface(ID3D11Texture2D *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11Texture2D_AddRef(ID3D11Texture2D *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11Texture2D_Release(ID3D11Texture2D *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11Texture2D_GetDevice(ID3D11Texture2D *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Texture2D, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Texture2D_GetPrivateData(ID3D11Texture2D *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Texture2D_SetPrivateData(ID3D11Texture2D *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Texture2D, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Texture2D_SetPrivateDataInterface(ID3D11Texture2D *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Texture2D, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static void STDMETHODCALLTYPE g_ID3D11Texture2D_GetType(ID3D11Texture2D *This, D3D11_RESOURCE_DIMENSION * pResourceDimension) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Texture2D, 7};
    packet.args[0] = guest_address(pResourceDimension);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11Texture2D_SetEvictionPriority(ID3D11Texture2D *This, UINT EvictionPriority) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Texture2D, 8};
    packet.args[0] = (uint32_t)EvictionPriority;
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static UINT STDMETHODCALLTYPE g_ID3D11Texture2D_GetEvictionPriority(ID3D11Texture2D *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Texture2D, 9};
    LONG status = proxy_call(&packet);
    if (status < 0) { return (UINT)status; }
    return (UINT)packet.ret;
}
static void STDMETHODCALLTYPE g_ID3D11Texture2D_GetDesc(ID3D11Texture2D *This, D3D11_TEXTURE2D_DESC * pDesc) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Texture2D, 10};
    packet.args[0] = guest_address(pDesc);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static const ID3D11Texture2DVtbl vtbl_ID3D11Texture2D = {
    g_ID3D11Texture2D_QueryInterface,
    g_ID3D11Texture2D_AddRef,
    g_ID3D11Texture2D_Release,
    g_ID3D11Texture2D_GetDevice,
    g_ID3D11Texture2D_GetPrivateData,
    g_ID3D11Texture2D_SetPrivateData,
    g_ID3D11Texture2D_SetPrivateDataInterface,
    g_ID3D11Texture2D_GetType,
    g_ID3D11Texture2D_SetEvictionPriority,
    g_ID3D11Texture2D_GetEvictionPriority,
    g_ID3D11Texture2D_GetDesc
};
static HRESULT STDMETHODCALLTYPE g_ID3D11Texture3D_QueryInterface(ID3D11Texture3D *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11Texture3D_AddRef(ID3D11Texture3D *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11Texture3D_Release(ID3D11Texture3D *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11Texture3D_GetDevice(ID3D11Texture3D *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Texture3D, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Texture3D_GetPrivateData(ID3D11Texture3D *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Texture3D_SetPrivateData(ID3D11Texture3D *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Texture3D, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11Texture3D_SetPrivateDataInterface(ID3D11Texture3D *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Texture3D, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static void STDMETHODCALLTYPE g_ID3D11Texture3D_GetType(ID3D11Texture3D *This, D3D11_RESOURCE_DIMENSION * pResourceDimension) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Texture3D, 7};
    packet.args[0] = guest_address(pResourceDimension);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11Texture3D_SetEvictionPriority(ID3D11Texture3D *This, UINT EvictionPriority) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Texture3D, 8};
    packet.args[0] = (uint32_t)EvictionPriority;
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static UINT STDMETHODCALLTYPE g_ID3D11Texture3D_GetEvictionPriority(ID3D11Texture3D *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Texture3D, 9};
    LONG status = proxy_call(&packet);
    if (status < 0) { return (UINT)status; }
    return (UINT)packet.ret;
}
static void STDMETHODCALLTYPE g_ID3D11Texture3D_GetDesc(ID3D11Texture3D *This, D3D11_TEXTURE3D_DESC * pDesc) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11Texture3D, 10};
    packet.args[0] = guest_address(pDesc);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static const ID3D11Texture3DVtbl vtbl_ID3D11Texture3D = {
    g_ID3D11Texture3D_QueryInterface,
    g_ID3D11Texture3D_AddRef,
    g_ID3D11Texture3D_Release,
    g_ID3D11Texture3D_GetDevice,
    g_ID3D11Texture3D_GetPrivateData,
    g_ID3D11Texture3D_SetPrivateData,
    g_ID3D11Texture3D_SetPrivateDataInterface,
    g_ID3D11Texture3D_GetType,
    g_ID3D11Texture3D_SetEvictionPriority,
    g_ID3D11Texture3D_GetEvictionPriority,
    g_ID3D11Texture3D_GetDesc
};
static HRESULT STDMETHODCALLTYPE g_ID3D11UnorderedAccessView_QueryInterface(ID3D11UnorderedAccessView *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11UnorderedAccessView_AddRef(ID3D11UnorderedAccessView *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11UnorderedAccessView_Release(ID3D11UnorderedAccessView *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11UnorderedAccessView_GetDevice(ID3D11UnorderedAccessView *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11UnorderedAccessView, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11UnorderedAccessView_GetPrivateData(ID3D11UnorderedAccessView *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11UnorderedAccessView_SetPrivateData(ID3D11UnorderedAccessView *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11UnorderedAccessView, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11UnorderedAccessView_SetPrivateDataInterface(ID3D11UnorderedAccessView *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11UnorderedAccessView, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static void STDMETHODCALLTYPE g_ID3D11UnorderedAccessView_GetResource(ID3D11UnorderedAccessView *This, ID3D11Resource ** ppResource) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11UnorderedAccessView, 7};
    struct proxy_output wire_ppResource;
    if (!proxy_output_init(&wire_ppResource,ppResource,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppResource.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppResource,ppResource,safe_array_count(1),SD_COM_IF_ID3D11Resource)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppResource,ppResource);
    proxy_output_dispose(&wire_ppResource,SD_COM_IF_ID3D11Resource);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static void STDMETHODCALLTYPE g_ID3D11UnorderedAccessView_GetDesc(ID3D11UnorderedAccessView *This, D3D11_UNORDERED_ACCESS_VIEW_DESC * pDesc) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11UnorderedAccessView, 8};
    packet.args[0] = guest_address(pDesc);
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static const ID3D11UnorderedAccessViewVtbl vtbl_ID3D11UnorderedAccessView = {
    g_ID3D11UnorderedAccessView_QueryInterface,
    g_ID3D11UnorderedAccessView_AddRef,
    g_ID3D11UnorderedAccessView_Release,
    g_ID3D11UnorderedAccessView_GetDevice,
    g_ID3D11UnorderedAccessView_GetPrivateData,
    g_ID3D11UnorderedAccessView_SetPrivateData,
    g_ID3D11UnorderedAccessView_SetPrivateDataInterface,
    g_ID3D11UnorderedAccessView_GetResource,
    g_ID3D11UnorderedAccessView_GetDesc
};
static HRESULT STDMETHODCALLTYPE g_ID3D11VertexShader_QueryInterface(ID3D11VertexShader *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11VertexShader_AddRef(ID3D11VertexShader *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11VertexShader_Release(ID3D11VertexShader *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11VertexShader_GetDevice(ID3D11VertexShader *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11VertexShader, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11VertexShader_GetPrivateData(ID3D11VertexShader *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11VertexShader_SetPrivateData(ID3D11VertexShader *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11VertexShader, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11VertexShader_SetPrivateDataInterface(ID3D11VertexShader *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11VertexShader, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static const ID3D11VertexShaderVtbl vtbl_ID3D11VertexShader = {
    g_ID3D11VertexShader_QueryInterface,
    g_ID3D11VertexShader_AddRef,
    g_ID3D11VertexShader_Release,
    g_ID3D11VertexShader_GetDevice,
    g_ID3D11VertexShader_GetPrivateData,
    g_ID3D11VertexShader_SetPrivateData,
    g_ID3D11VertexShader_SetPrivateDataInterface
};
static HRESULT STDMETHODCALLTYPE g_ID3D11View_QueryInterface(ID3D11View *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_ID3D11View_AddRef(ID3D11View *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_ID3D11View_Release(ID3D11View *This) {
    return proxy_release(This);
}
static void STDMETHODCALLTYPE g_ID3D11View_GetDevice(ID3D11View *This, ID3D11Device ** ppDevice) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11View, 3};
    struct proxy_output wire_ppDevice;
    if (!proxy_output_init(&wire_ppDevice,ppDevice,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppDevice.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppDevice,ppDevice,safe_array_count(1),SD_COM_IF_ID3D11Device)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppDevice,ppDevice);
    proxy_output_dispose(&wire_ppDevice,SD_COM_IF_ID3D11Device);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11View_GetPrivateData(ID3D11View *This, REFGUID guid, UINT * pDataSize, void * pData) {
    return proxy_private_get(This, 4, guid, pDataSize, pData);
}
static HRESULT STDMETHODCALLTYPE g_ID3D11View_SetPrivateData(ID3D11View *This, REFGUID guid, UINT DataSize, const void * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11View, 5};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)DataSize;
    packet.args[2] = guest_address(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_ID3D11View_SetPrivateDataInterface(ID3D11View *This, REFGUID guid, const IUnknown * pData) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11View, 6};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(pData);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static void STDMETHODCALLTYPE g_ID3D11View_GetResource(ID3D11View *This, ID3D11Resource ** ppResource) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_ID3D11View, 7};
    struct proxy_output wire_ppResource;
    if (!proxy_output_init(&wire_ppResource,ppResource,safe_array_count(1))) {  proxy_fatal(E_OUTOFMEMORY); return; }
    packet.args[0] = guest_address(wire_ppResource.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && !proxy_output_publish(&wire_ppResource,ppResource,safe_array_count(1),SD_COM_IF_ID3D11Resource)) status=E_OUTOFMEMORY;
    if (!(status >= 0)) proxy_output_retract(&wire_ppResource,ppResource);
    proxy_output_dispose(&wire_ppResource,SD_COM_IF_ID3D11Resource);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static const ID3D11ViewVtbl vtbl_ID3D11View = {
    g_ID3D11View_QueryInterface,
    g_ID3D11View_AddRef,
    g_ID3D11View_Release,
    g_ID3D11View_GetDevice,
    g_ID3D11View_GetPrivateData,
    g_ID3D11View_SetPrivateData,
    g_ID3D11View_SetPrivateDataInterface,
    g_ID3D11View_GetResource
};
static HRESULT STDMETHODCALLTYPE g_IDXGIAdapter_QueryInterface(IDXGIAdapter *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_IDXGIAdapter_AddRef(IDXGIAdapter *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_IDXGIAdapter_Release(IDXGIAdapter *This) {
    return proxy_release(This);
}
static HRESULT STDMETHODCALLTYPE g_IDXGIAdapter_SetPrivateData(IDXGIAdapter *This, REFGUID guid, UINT data_size, const void * data) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIAdapter, 3};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)data_size;
    packet.args[2] = guest_address(data);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIAdapter_SetPrivateDataInterface(IDXGIAdapter *This, REFGUID guid, const IUnknown * object) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIAdapter, 4};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(object);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIAdapter_GetPrivateData(IDXGIAdapter *This, REFGUID guid, UINT * data_size, void * data) {
    return proxy_private_get(This, 5, guid, data_size, data);
}
static HRESULT STDMETHODCALLTYPE g_IDXGIAdapter_GetParent(IDXGIAdapter *This, REFIID riid, void ** parent) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIAdapter, 6};
    packet.args[0] = guest_address(riid);
    struct proxy_output wire_parent;
    if (!proxy_output_init(&wire_parent,parent,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_parent.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_parent,parent,safe_array_count(1),proxy_iid(riid))) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_parent,parent);
    proxy_output_dispose(&wire_parent,proxy_iid(riid));
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIAdapter_EnumOutputs(IDXGIAdapter *This, UINT output_idx, IDXGIOutput ** output) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIAdapter, 7};
    packet.args[0] = (uint32_t)output_idx;
    struct proxy_output wire_output;
    if (!proxy_output_init(&wire_output,output,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_output.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_output,output,safe_array_count(1),SD_COM_IF_IDXGIOutput)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_output,output);
    proxy_output_dispose(&wire_output,SD_COM_IF_IDXGIOutput);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIAdapter_GetDesc(IDXGIAdapter *This, DXGI_ADAPTER_DESC * desc) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIAdapter, 8};
    packet.args[0] = guest_address(desc);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIAdapter_CheckInterfaceSupport(IDXGIAdapter *This, REFGUID guid, LARGE_INTEGER * umd_version) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIAdapter, 9};
    packet.args[0] = guest_address(guid);
    packet.args[1] = guest_address(umd_version);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static const IDXGIAdapterVtbl vtbl_IDXGIAdapter = {
    g_IDXGIAdapter_QueryInterface,
    g_IDXGIAdapter_AddRef,
    g_IDXGIAdapter_Release,
    g_IDXGIAdapter_SetPrivateData,
    g_IDXGIAdapter_SetPrivateDataInterface,
    g_IDXGIAdapter_GetPrivateData,
    g_IDXGIAdapter_GetParent,
    g_IDXGIAdapter_EnumOutputs,
    g_IDXGIAdapter_GetDesc,
    g_IDXGIAdapter_CheckInterfaceSupport
};
static HRESULT STDMETHODCALLTYPE g_IDXGIAdapter1_QueryInterface(IDXGIAdapter1 *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_IDXGIAdapter1_AddRef(IDXGIAdapter1 *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_IDXGIAdapter1_Release(IDXGIAdapter1 *This) {
    return proxy_release(This);
}
static HRESULT STDMETHODCALLTYPE g_IDXGIAdapter1_SetPrivateData(IDXGIAdapter1 *This, REFGUID guid, UINT data_size, const void * data) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIAdapter1, 3};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)data_size;
    packet.args[2] = guest_address(data);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIAdapter1_SetPrivateDataInterface(IDXGIAdapter1 *This, REFGUID guid, const IUnknown * object) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIAdapter1, 4};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(object);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIAdapter1_GetPrivateData(IDXGIAdapter1 *This, REFGUID guid, UINT * data_size, void * data) {
    return proxy_private_get(This, 5, guid, data_size, data);
}
static HRESULT STDMETHODCALLTYPE g_IDXGIAdapter1_GetParent(IDXGIAdapter1 *This, REFIID riid, void ** parent) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIAdapter1, 6};
    packet.args[0] = guest_address(riid);
    struct proxy_output wire_parent;
    if (!proxy_output_init(&wire_parent,parent,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_parent.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_parent,parent,safe_array_count(1),proxy_iid(riid))) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_parent,parent);
    proxy_output_dispose(&wire_parent,proxy_iid(riid));
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIAdapter1_EnumOutputs(IDXGIAdapter1 *This, UINT output_idx, IDXGIOutput ** output) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIAdapter1, 7};
    packet.args[0] = (uint32_t)output_idx;
    struct proxy_output wire_output;
    if (!proxy_output_init(&wire_output,output,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_output.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_output,output,safe_array_count(1),SD_COM_IF_IDXGIOutput)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_output,output);
    proxy_output_dispose(&wire_output,SD_COM_IF_IDXGIOutput);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIAdapter1_GetDesc(IDXGIAdapter1 *This, DXGI_ADAPTER_DESC * desc) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIAdapter1, 8};
    packet.args[0] = guest_address(desc);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIAdapter1_CheckInterfaceSupport(IDXGIAdapter1 *This, REFGUID guid, LARGE_INTEGER * umd_version) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIAdapter1, 9};
    packet.args[0] = guest_address(guid);
    packet.args[1] = guest_address(umd_version);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIAdapter1_GetDesc1(IDXGIAdapter1 *This, DXGI_ADAPTER_DESC1 * pDesc) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIAdapter1, 10};
    packet.args[0] = guest_address(pDesc);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static const IDXGIAdapter1Vtbl vtbl_IDXGIAdapter1 = {
    g_IDXGIAdapter1_QueryInterface,
    g_IDXGIAdapter1_AddRef,
    g_IDXGIAdapter1_Release,
    g_IDXGIAdapter1_SetPrivateData,
    g_IDXGIAdapter1_SetPrivateDataInterface,
    g_IDXGIAdapter1_GetPrivateData,
    g_IDXGIAdapter1_GetParent,
    g_IDXGIAdapter1_EnumOutputs,
    g_IDXGIAdapter1_GetDesc,
    g_IDXGIAdapter1_CheckInterfaceSupport,
    g_IDXGIAdapter1_GetDesc1
};
static HRESULT STDMETHODCALLTYPE g_IDXGIDevice_QueryInterface(IDXGIDevice *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_IDXGIDevice_AddRef(IDXGIDevice *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_IDXGIDevice_Release(IDXGIDevice *This) {
    return proxy_release(This);
}
static HRESULT STDMETHODCALLTYPE g_IDXGIDevice_SetPrivateData(IDXGIDevice *This, REFGUID guid, UINT data_size, const void * data) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIDevice, 3};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)data_size;
    packet.args[2] = guest_address(data);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIDevice_SetPrivateDataInterface(IDXGIDevice *This, REFGUID guid, const IUnknown * object) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIDevice, 4};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(object);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIDevice_GetPrivateData(IDXGIDevice *This, REFGUID guid, UINT * data_size, void * data) {
    return proxy_private_get(This, 5, guid, data_size, data);
}
static HRESULT STDMETHODCALLTYPE g_IDXGIDevice_GetParent(IDXGIDevice *This, REFIID riid, void ** parent) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIDevice, 6};
    packet.args[0] = guest_address(riid);
    struct proxy_output wire_parent;
    if (!proxy_output_init(&wire_parent,parent,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_parent.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_parent,parent,safe_array_count(1),proxy_iid(riid))) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_parent,parent);
    proxy_output_dispose(&wire_parent,proxy_iid(riid));
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIDevice_GetAdapter(IDXGIDevice *This, IDXGIAdapter ** adapter) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIDevice, 7};
    struct proxy_output wire_adapter;
    if (!proxy_output_init(&wire_adapter,adapter,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[0] = guest_address(wire_adapter.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_adapter,adapter,safe_array_count(1),SD_COM_IF_IDXGIAdapter)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_adapter,adapter);
    proxy_output_dispose(&wire_adapter,SD_COM_IF_IDXGIAdapter);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIDevice_CreateSurface(IDXGIDevice *This, const DXGI_SURFACE_DESC * desc, UINT surface_count, DXGI_USAGE usage, const DXGI_SHARED_RESOURCE * shared_resource, IDXGISurface ** surface) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIDevice, 8};
    packet.args[0] = guest_address(desc);
    packet.args[1] = (uint32_t)surface_count;
    packet.args[2] = (uint32_t)usage;
    packet.args[3] = guest_address(shared_resource);
    struct proxy_output wire_surface;
    if (!proxy_output_init(&wire_surface,surface,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[4] = guest_address(wire_surface.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_surface,surface,safe_array_count(1),SD_COM_IF_IDXGISurface)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_surface,surface);
    proxy_output_dispose(&wire_surface,SD_COM_IF_IDXGISurface);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIDevice_QueryResourceResidency(IDXGIDevice *This, IUnknown *const * resources, DXGI_RESIDENCY * residency, UINT resource_count) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIDevice, 9};
    UINT count_resources = safe_array_count(1);
    uint32_t stack_resources[128];
    uint32_t *tokens_resources = resources && count_resources ? (count_resources<=128 ? stack_resources : HeapAlloc(GetProcessHeap(), 0, count_resources*4)) : NULL;
    if (resources && count_resources && !tokens_resources) {  return (HRESULT)E_OUTOFMEMORY; }
    for (UINT i=0; i<count_resources && resources; ++i) tokens_resources[i] = proxy_token(resources[i]);
    packet.args[0] = guest_address(tokens_resources);
    packet.args[1] = guest_address(residency);
    packet.args[2] = (uint32_t)resource_count;
    LONG status = proxy_call(&packet);
    if (tokens_resources && count_resources>128) HeapFree(GetProcessHeap(), 0, tokens_resources);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIDevice_SetGPUThreadPriority(IDXGIDevice *This, INT priority) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIDevice, 10};
    packet.args[0] = (uint32_t)priority;
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIDevice_GetGPUThreadPriority(IDXGIDevice *This, INT * priority) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIDevice, 11};
    packet.args[0] = guest_address(priority);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static const IDXGIDeviceVtbl vtbl_IDXGIDevice = {
    g_IDXGIDevice_QueryInterface,
    g_IDXGIDevice_AddRef,
    g_IDXGIDevice_Release,
    g_IDXGIDevice_SetPrivateData,
    g_IDXGIDevice_SetPrivateDataInterface,
    g_IDXGIDevice_GetPrivateData,
    g_IDXGIDevice_GetParent,
    g_IDXGIDevice_GetAdapter,
    g_IDXGIDevice_CreateSurface,
    g_IDXGIDevice_QueryResourceResidency,
    g_IDXGIDevice_SetGPUThreadPriority,
    g_IDXGIDevice_GetGPUThreadPriority
};
static HRESULT STDMETHODCALLTYPE g_IDXGIDevice1_QueryInterface(IDXGIDevice1 *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_IDXGIDevice1_AddRef(IDXGIDevice1 *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_IDXGIDevice1_Release(IDXGIDevice1 *This) {
    return proxy_release(This);
}
static HRESULT STDMETHODCALLTYPE g_IDXGIDevice1_SetPrivateData(IDXGIDevice1 *This, REFGUID guid, UINT data_size, const void * data) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIDevice1, 3};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)data_size;
    packet.args[2] = guest_address(data);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIDevice1_SetPrivateDataInterface(IDXGIDevice1 *This, REFGUID guid, const IUnknown * object) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIDevice1, 4};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(object);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIDevice1_GetPrivateData(IDXGIDevice1 *This, REFGUID guid, UINT * data_size, void * data) {
    return proxy_private_get(This, 5, guid, data_size, data);
}
static HRESULT STDMETHODCALLTYPE g_IDXGIDevice1_GetParent(IDXGIDevice1 *This, REFIID riid, void ** parent) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIDevice1, 6};
    packet.args[0] = guest_address(riid);
    struct proxy_output wire_parent;
    if (!proxy_output_init(&wire_parent,parent,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_parent.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_parent,parent,safe_array_count(1),proxy_iid(riid))) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_parent,parent);
    proxy_output_dispose(&wire_parent,proxy_iid(riid));
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIDevice1_GetAdapter(IDXGIDevice1 *This, IDXGIAdapter ** adapter) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIDevice1, 7};
    struct proxy_output wire_adapter;
    if (!proxy_output_init(&wire_adapter,adapter,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[0] = guest_address(wire_adapter.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_adapter,adapter,safe_array_count(1),SD_COM_IF_IDXGIAdapter)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_adapter,adapter);
    proxy_output_dispose(&wire_adapter,SD_COM_IF_IDXGIAdapter);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIDevice1_CreateSurface(IDXGIDevice1 *This, const DXGI_SURFACE_DESC * desc, UINT surface_count, DXGI_USAGE usage, const DXGI_SHARED_RESOURCE * shared_resource, IDXGISurface ** surface) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIDevice1, 8};
    packet.args[0] = guest_address(desc);
    packet.args[1] = (uint32_t)surface_count;
    packet.args[2] = (uint32_t)usage;
    packet.args[3] = guest_address(shared_resource);
    struct proxy_output wire_surface;
    if (!proxy_output_init(&wire_surface,surface,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[4] = guest_address(wire_surface.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_surface,surface,safe_array_count(1),SD_COM_IF_IDXGISurface)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_surface,surface);
    proxy_output_dispose(&wire_surface,SD_COM_IF_IDXGISurface);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIDevice1_QueryResourceResidency(IDXGIDevice1 *This, IUnknown *const * resources, DXGI_RESIDENCY * residency, UINT resource_count) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIDevice1, 9};
    UINT count_resources = safe_array_count(1);
    uint32_t stack_resources[128];
    uint32_t *tokens_resources = resources && count_resources ? (count_resources<=128 ? stack_resources : HeapAlloc(GetProcessHeap(), 0, count_resources*4)) : NULL;
    if (resources && count_resources && !tokens_resources) {  return (HRESULT)E_OUTOFMEMORY; }
    for (UINT i=0; i<count_resources && resources; ++i) tokens_resources[i] = proxy_token(resources[i]);
    packet.args[0] = guest_address(tokens_resources);
    packet.args[1] = guest_address(residency);
    packet.args[2] = (uint32_t)resource_count;
    LONG status = proxy_call(&packet);
    if (tokens_resources && count_resources>128) HeapFree(GetProcessHeap(), 0, tokens_resources);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIDevice1_SetGPUThreadPriority(IDXGIDevice1 *This, INT priority) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIDevice1, 10};
    packet.args[0] = (uint32_t)priority;
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIDevice1_GetGPUThreadPriority(IDXGIDevice1 *This, INT * priority) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIDevice1, 11};
    packet.args[0] = guest_address(priority);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIDevice1_SetMaximumFrameLatency(IDXGIDevice1 *This, UINT MaxLatency) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIDevice1, 12};
    packet.args[0] = (uint32_t)MaxLatency;
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIDevice1_GetMaximumFrameLatency(IDXGIDevice1 *This, UINT * pMaxLatency) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIDevice1, 13};
    packet.args[0] = guest_address(pMaxLatency);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static const IDXGIDevice1Vtbl vtbl_IDXGIDevice1 = {
    g_IDXGIDevice1_QueryInterface,
    g_IDXGIDevice1_AddRef,
    g_IDXGIDevice1_Release,
    g_IDXGIDevice1_SetPrivateData,
    g_IDXGIDevice1_SetPrivateDataInterface,
    g_IDXGIDevice1_GetPrivateData,
    g_IDXGIDevice1_GetParent,
    g_IDXGIDevice1_GetAdapter,
    g_IDXGIDevice1_CreateSurface,
    g_IDXGIDevice1_QueryResourceResidency,
    g_IDXGIDevice1_SetGPUThreadPriority,
    g_IDXGIDevice1_GetGPUThreadPriority,
    g_IDXGIDevice1_SetMaximumFrameLatency,
    g_IDXGIDevice1_GetMaximumFrameLatency
};
static HRESULT STDMETHODCALLTYPE g_IDXGIDeviceSubObject_QueryInterface(IDXGIDeviceSubObject *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_IDXGIDeviceSubObject_AddRef(IDXGIDeviceSubObject *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_IDXGIDeviceSubObject_Release(IDXGIDeviceSubObject *This) {
    return proxy_release(This);
}
static HRESULT STDMETHODCALLTYPE g_IDXGIDeviceSubObject_SetPrivateData(IDXGIDeviceSubObject *This, REFGUID guid, UINT data_size, const void * data) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIDeviceSubObject, 3};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)data_size;
    packet.args[2] = guest_address(data);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIDeviceSubObject_SetPrivateDataInterface(IDXGIDeviceSubObject *This, REFGUID guid, const IUnknown * object) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIDeviceSubObject, 4};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(object);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIDeviceSubObject_GetPrivateData(IDXGIDeviceSubObject *This, REFGUID guid, UINT * data_size, void * data) {
    return proxy_private_get(This, 5, guid, data_size, data);
}
static HRESULT STDMETHODCALLTYPE g_IDXGIDeviceSubObject_GetParent(IDXGIDeviceSubObject *This, REFIID riid, void ** parent) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIDeviceSubObject, 6};
    packet.args[0] = guest_address(riid);
    struct proxy_output wire_parent;
    if (!proxy_output_init(&wire_parent,parent,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_parent.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_parent,parent,safe_array_count(1),proxy_iid(riid))) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_parent,parent);
    proxy_output_dispose(&wire_parent,proxy_iid(riid));
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIDeviceSubObject_GetDevice(IDXGIDeviceSubObject *This, REFIID riid, void ** device) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIDeviceSubObject, 7};
    packet.args[0] = guest_address(riid);
    struct proxy_output wire_device;
    if (!proxy_output_init(&wire_device,device,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_device.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_device,device,safe_array_count(1),proxy_iid(riid))) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_device,device);
    proxy_output_dispose(&wire_device,proxy_iid(riid));
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static const IDXGIDeviceSubObjectVtbl vtbl_IDXGIDeviceSubObject = {
    g_IDXGIDeviceSubObject_QueryInterface,
    g_IDXGIDeviceSubObject_AddRef,
    g_IDXGIDeviceSubObject_Release,
    g_IDXGIDeviceSubObject_SetPrivateData,
    g_IDXGIDeviceSubObject_SetPrivateDataInterface,
    g_IDXGIDeviceSubObject_GetPrivateData,
    g_IDXGIDeviceSubObject_GetParent,
    g_IDXGIDeviceSubObject_GetDevice
};
static HRESULT STDMETHODCALLTYPE g_IDXGIFactory_QueryInterface(IDXGIFactory *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_IDXGIFactory_AddRef(IDXGIFactory *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_IDXGIFactory_Release(IDXGIFactory *This) {
    return proxy_release(This);
}
static HRESULT STDMETHODCALLTYPE g_IDXGIFactory_SetPrivateData(IDXGIFactory *This, REFGUID guid, UINT data_size, const void * data) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIFactory, 3};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)data_size;
    packet.args[2] = guest_address(data);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIFactory_SetPrivateDataInterface(IDXGIFactory *This, REFGUID guid, const IUnknown * object) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIFactory, 4};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(object);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIFactory_GetPrivateData(IDXGIFactory *This, REFGUID guid, UINT * data_size, void * data) {
    return proxy_private_get(This, 5, guid, data_size, data);
}
static HRESULT STDMETHODCALLTYPE g_IDXGIFactory_GetParent(IDXGIFactory *This, REFIID riid, void ** parent) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIFactory, 6};
    packet.args[0] = guest_address(riid);
    struct proxy_output wire_parent;
    if (!proxy_output_init(&wire_parent,parent,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_parent.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_parent,parent,safe_array_count(1),proxy_iid(riid))) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_parent,parent);
    proxy_output_dispose(&wire_parent,proxy_iid(riid));
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIFactory_EnumAdapters(IDXGIFactory *This, UINT adapter_idx, IDXGIAdapter ** adapter) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIFactory, 7};
    packet.args[0] = (uint32_t)adapter_idx;
    struct proxy_output wire_adapter;
    if (!proxy_output_init(&wire_adapter,adapter,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_adapter.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_adapter,adapter,safe_array_count(1),SD_COM_IF_IDXGIAdapter)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_adapter,adapter);
    proxy_output_dispose(&wire_adapter,SD_COM_IF_IDXGIAdapter);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIFactory_MakeWindowAssociation(IDXGIFactory *This, HWND window, UINT flags) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIFactory, 8};
    packet.args[0] = guest_address(window);
    packet.args[1] = (uint32_t)flags;
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIFactory_GetWindowAssociation(IDXGIFactory *This, HWND * window) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIFactory, 9};
    packet.args[0] = guest_address(window);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIFactory_CreateSwapChain(IDXGIFactory *This, IUnknown * device, DXGI_SWAP_CHAIN_DESC * desc, IDXGISwapChain ** swapchain) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIFactory, 10};
    packet.args[0] = proxy_token(device);
    packet.args[1] = guest_address(desc);
    struct proxy_output wire_swapchain;
    if (!proxy_output_init(&wire_swapchain,swapchain,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[2] = guest_address(wire_swapchain.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_swapchain,swapchain,safe_array_count(1),SD_COM_IF_IDXGISwapChain)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_swapchain,swapchain);
    proxy_output_dispose(&wire_swapchain,SD_COM_IF_IDXGISwapChain);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIFactory_CreateSoftwareAdapter(IDXGIFactory *This, HMODULE swrast, IDXGIAdapter ** adapter) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIFactory, 11};
    packet.args[0] = guest_address(swrast);
    struct proxy_output wire_adapter;
    if (!proxy_output_init(&wire_adapter,adapter,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_adapter.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_adapter,adapter,safe_array_count(1),SD_COM_IF_IDXGIAdapter)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_adapter,adapter);
    proxy_output_dispose(&wire_adapter,SD_COM_IF_IDXGIAdapter);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static const IDXGIFactoryVtbl vtbl_IDXGIFactory = {
    g_IDXGIFactory_QueryInterface,
    g_IDXGIFactory_AddRef,
    g_IDXGIFactory_Release,
    g_IDXGIFactory_SetPrivateData,
    g_IDXGIFactory_SetPrivateDataInterface,
    g_IDXGIFactory_GetPrivateData,
    g_IDXGIFactory_GetParent,
    g_IDXGIFactory_EnumAdapters,
    g_IDXGIFactory_MakeWindowAssociation,
    g_IDXGIFactory_GetWindowAssociation,
    g_IDXGIFactory_CreateSwapChain,
    g_IDXGIFactory_CreateSoftwareAdapter
};
static HRESULT STDMETHODCALLTYPE g_IDXGIFactory1_QueryInterface(IDXGIFactory1 *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_IDXGIFactory1_AddRef(IDXGIFactory1 *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_IDXGIFactory1_Release(IDXGIFactory1 *This) {
    return proxy_release(This);
}
static HRESULT STDMETHODCALLTYPE g_IDXGIFactory1_SetPrivateData(IDXGIFactory1 *This, REFGUID guid, UINT data_size, const void * data) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIFactory1, 3};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)data_size;
    packet.args[2] = guest_address(data);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIFactory1_SetPrivateDataInterface(IDXGIFactory1 *This, REFGUID guid, const IUnknown * object) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIFactory1, 4};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(object);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIFactory1_GetPrivateData(IDXGIFactory1 *This, REFGUID guid, UINT * data_size, void * data) {
    return proxy_private_get(This, 5, guid, data_size, data);
}
static HRESULT STDMETHODCALLTYPE g_IDXGIFactory1_GetParent(IDXGIFactory1 *This, REFIID riid, void ** parent) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIFactory1, 6};
    packet.args[0] = guest_address(riid);
    struct proxy_output wire_parent;
    if (!proxy_output_init(&wire_parent,parent,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_parent.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_parent,parent,safe_array_count(1),proxy_iid(riid))) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_parent,parent);
    proxy_output_dispose(&wire_parent,proxy_iid(riid));
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIFactory1_EnumAdapters(IDXGIFactory1 *This, UINT adapter_idx, IDXGIAdapter ** adapter) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIFactory1, 7};
    packet.args[0] = (uint32_t)adapter_idx;
    struct proxy_output wire_adapter;
    if (!proxy_output_init(&wire_adapter,adapter,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_adapter.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_adapter,adapter,safe_array_count(1),SD_COM_IF_IDXGIAdapter)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_adapter,adapter);
    proxy_output_dispose(&wire_adapter,SD_COM_IF_IDXGIAdapter);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIFactory1_MakeWindowAssociation(IDXGIFactory1 *This, HWND window, UINT flags) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIFactory1, 8};
    packet.args[0] = guest_address(window);
    packet.args[1] = (uint32_t)flags;
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIFactory1_GetWindowAssociation(IDXGIFactory1 *This, HWND * window) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIFactory1, 9};
    packet.args[0] = guest_address(window);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIFactory1_CreateSwapChain(IDXGIFactory1 *This, IUnknown * device, DXGI_SWAP_CHAIN_DESC * desc, IDXGISwapChain ** swapchain) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIFactory1, 10};
    packet.args[0] = proxy_token(device);
    packet.args[1] = guest_address(desc);
    struct proxy_output wire_swapchain;
    if (!proxy_output_init(&wire_swapchain,swapchain,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[2] = guest_address(wire_swapchain.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_swapchain,swapchain,safe_array_count(1),SD_COM_IF_IDXGISwapChain)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_swapchain,swapchain);
    proxy_output_dispose(&wire_swapchain,SD_COM_IF_IDXGISwapChain);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIFactory1_CreateSoftwareAdapter(IDXGIFactory1 *This, HMODULE swrast, IDXGIAdapter ** adapter) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIFactory1, 11};
    packet.args[0] = guest_address(swrast);
    struct proxy_output wire_adapter;
    if (!proxy_output_init(&wire_adapter,adapter,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_adapter.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_adapter,adapter,safe_array_count(1),SD_COM_IF_IDXGIAdapter)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_adapter,adapter);
    proxy_output_dispose(&wire_adapter,SD_COM_IF_IDXGIAdapter);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIFactory1_EnumAdapters1(IDXGIFactory1 *This, UINT Adapter, IDXGIAdapter1 ** ppAdapter) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIFactory1, 12};
    packet.args[0] = (uint32_t)Adapter;
    struct proxy_output wire_ppAdapter;
    if (!proxy_output_init(&wire_ppAdapter,ppAdapter,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_ppAdapter.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_ppAdapter,ppAdapter,safe_array_count(1),SD_COM_IF_IDXGIAdapter1)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_ppAdapter,ppAdapter);
    proxy_output_dispose(&wire_ppAdapter,SD_COM_IF_IDXGIAdapter1);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static WINBOOL STDMETHODCALLTYPE g_IDXGIFactory1_IsCurrent(IDXGIFactory1 *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIFactory1, 13};
    LONG status = proxy_call(&packet);
    if (status < 0) { return (WINBOOL)status; }
    return (WINBOOL)packet.ret;
}
static const IDXGIFactory1Vtbl vtbl_IDXGIFactory1 = {
    g_IDXGIFactory1_QueryInterface,
    g_IDXGIFactory1_AddRef,
    g_IDXGIFactory1_Release,
    g_IDXGIFactory1_SetPrivateData,
    g_IDXGIFactory1_SetPrivateDataInterface,
    g_IDXGIFactory1_GetPrivateData,
    g_IDXGIFactory1_GetParent,
    g_IDXGIFactory1_EnumAdapters,
    g_IDXGIFactory1_MakeWindowAssociation,
    g_IDXGIFactory1_GetWindowAssociation,
    g_IDXGIFactory1_CreateSwapChain,
    g_IDXGIFactory1_CreateSoftwareAdapter,
    g_IDXGIFactory1_EnumAdapters1,
    g_IDXGIFactory1_IsCurrent
};
static HRESULT STDMETHODCALLTYPE g_IDXGIKeyedMutex_QueryInterface(IDXGIKeyedMutex *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_IDXGIKeyedMutex_AddRef(IDXGIKeyedMutex *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_IDXGIKeyedMutex_Release(IDXGIKeyedMutex *This) {
    return proxy_release(This);
}
static HRESULT STDMETHODCALLTYPE g_IDXGIKeyedMutex_SetPrivateData(IDXGIKeyedMutex *This, REFGUID guid, UINT data_size, const void * data) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIKeyedMutex, 3};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)data_size;
    packet.args[2] = guest_address(data);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIKeyedMutex_SetPrivateDataInterface(IDXGIKeyedMutex *This, REFGUID guid, const IUnknown * object) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIKeyedMutex, 4};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(object);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIKeyedMutex_GetPrivateData(IDXGIKeyedMutex *This, REFGUID guid, UINT * data_size, void * data) {
    return proxy_private_get(This, 5, guid, data_size, data);
}
static HRESULT STDMETHODCALLTYPE g_IDXGIKeyedMutex_GetParent(IDXGIKeyedMutex *This, REFIID riid, void ** parent) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIKeyedMutex, 6};
    packet.args[0] = guest_address(riid);
    struct proxy_output wire_parent;
    if (!proxy_output_init(&wire_parent,parent,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_parent.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_parent,parent,safe_array_count(1),proxy_iid(riid))) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_parent,parent);
    proxy_output_dispose(&wire_parent,proxy_iid(riid));
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIKeyedMutex_GetDevice(IDXGIKeyedMutex *This, REFIID riid, void ** device) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIKeyedMutex, 7};
    packet.args[0] = guest_address(riid);
    struct proxy_output wire_device;
    if (!proxy_output_init(&wire_device,device,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_device.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_device,device,safe_array_count(1),proxy_iid(riid))) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_device,device);
    proxy_output_dispose(&wire_device,proxy_iid(riid));
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIKeyedMutex_AcquireSync(IDXGIKeyedMutex *This, UINT64 Key, DWORD dwMilliseconds) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIKeyedMutex, 8};
    packet.args[0] = (uint32_t)Key;
    packet.high[0] = (uint32_t)(Key >> 32);
    packet.args[1] = (uint32_t)dwMilliseconds;
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIKeyedMutex_ReleaseSync(IDXGIKeyedMutex *This, UINT64 Key) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIKeyedMutex, 9};
    packet.args[0] = (uint32_t)Key;
    packet.high[0] = (uint32_t)(Key >> 32);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static const IDXGIKeyedMutexVtbl vtbl_IDXGIKeyedMutex = {
    g_IDXGIKeyedMutex_QueryInterface,
    g_IDXGIKeyedMutex_AddRef,
    g_IDXGIKeyedMutex_Release,
    g_IDXGIKeyedMutex_SetPrivateData,
    g_IDXGIKeyedMutex_SetPrivateDataInterface,
    g_IDXGIKeyedMutex_GetPrivateData,
    g_IDXGIKeyedMutex_GetParent,
    g_IDXGIKeyedMutex_GetDevice,
    g_IDXGIKeyedMutex_AcquireSync,
    g_IDXGIKeyedMutex_ReleaseSync
};
static HRESULT STDMETHODCALLTYPE g_IDXGIObject_QueryInterface(IDXGIObject *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_IDXGIObject_AddRef(IDXGIObject *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_IDXGIObject_Release(IDXGIObject *This) {
    return proxy_release(This);
}
static HRESULT STDMETHODCALLTYPE g_IDXGIObject_SetPrivateData(IDXGIObject *This, REFGUID guid, UINT data_size, const void * data) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIObject, 3};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)data_size;
    packet.args[2] = guest_address(data);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIObject_SetPrivateDataInterface(IDXGIObject *This, REFGUID guid, const IUnknown * object) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIObject, 4};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(object);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIObject_GetPrivateData(IDXGIObject *This, REFGUID guid, UINT * data_size, void * data) {
    return proxy_private_get(This, 5, guid, data_size, data);
}
static HRESULT STDMETHODCALLTYPE g_IDXGIObject_GetParent(IDXGIObject *This, REFIID riid, void ** parent) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIObject, 6};
    packet.args[0] = guest_address(riid);
    struct proxy_output wire_parent;
    if (!proxy_output_init(&wire_parent,parent,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_parent.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_parent,parent,safe_array_count(1),proxy_iid(riid))) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_parent,parent);
    proxy_output_dispose(&wire_parent,proxy_iid(riid));
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static const IDXGIObjectVtbl vtbl_IDXGIObject = {
    g_IDXGIObject_QueryInterface,
    g_IDXGIObject_AddRef,
    g_IDXGIObject_Release,
    g_IDXGIObject_SetPrivateData,
    g_IDXGIObject_SetPrivateDataInterface,
    g_IDXGIObject_GetPrivateData,
    g_IDXGIObject_GetParent
};
static HRESULT STDMETHODCALLTYPE g_IDXGIOutput_QueryInterface(IDXGIOutput *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_IDXGIOutput_AddRef(IDXGIOutput *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_IDXGIOutput_Release(IDXGIOutput *This) {
    return proxy_release(This);
}
static HRESULT STDMETHODCALLTYPE g_IDXGIOutput_SetPrivateData(IDXGIOutput *This, REFGUID guid, UINT data_size, const void * data) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIOutput, 3};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)data_size;
    packet.args[2] = guest_address(data);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIOutput_SetPrivateDataInterface(IDXGIOutput *This, REFGUID guid, const IUnknown * object) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIOutput, 4};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(object);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIOutput_GetPrivateData(IDXGIOutput *This, REFGUID guid, UINT * data_size, void * data) {
    return proxy_private_get(This, 5, guid, data_size, data);
}
static HRESULT STDMETHODCALLTYPE g_IDXGIOutput_GetParent(IDXGIOutput *This, REFIID riid, void ** parent) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIOutput, 6};
    packet.args[0] = guest_address(riid);
    struct proxy_output wire_parent;
    if (!proxy_output_init(&wire_parent,parent,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_parent.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_parent,parent,safe_array_count(1),proxy_iid(riid))) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_parent,parent);
    proxy_output_dispose(&wire_parent,proxy_iid(riid));
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIOutput_GetDesc(IDXGIOutput *This, DXGI_OUTPUT_DESC * desc) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIOutput, 7};
    packet.args[0] = guest_address(desc);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    if (desc && SUCCEEDED((HRESULT)packet.ret)) desc->Monitor = MonitorFromWindow(NULL, MONITOR_DEFAULTTOPRIMARY);
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIOutput_GetDisplayModeList(IDXGIOutput *This, DXGI_FORMAT format, UINT flags, UINT * mode_count, DXGI_MODE_DESC * desc) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIOutput, 8};
    packet.args[0] = (uint32_t)format;
    packet.args[1] = (uint32_t)flags;
    packet.args[2] = guest_address(mode_count);
    packet.args[3] = guest_address(desc);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIOutput_FindClosestMatchingMode(IDXGIOutput *This, const DXGI_MODE_DESC * mode, DXGI_MODE_DESC * closest_match, IUnknown * device) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIOutput, 9};
    packet.args[0] = guest_address(mode);
    packet.args[1] = guest_address(closest_match);
    packet.args[2] = proxy_token(device);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIOutput_WaitForVBlank(IDXGIOutput *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIOutput, 10};
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIOutput_TakeOwnership(IDXGIOutput *This, IUnknown * device, WINBOOL exclusive) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIOutput, 11};
    packet.args[0] = proxy_token(device);
    packet.args[1] = (uint32_t)exclusive;
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static void STDMETHODCALLTYPE g_IDXGIOutput_ReleaseOwnership(IDXGIOutput *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIOutput, 12};
    LONG status = proxy_call(&packet);
    if (status < 0) { proxy_fatal(status); return; }
    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);
}
static HRESULT STDMETHODCALLTYPE g_IDXGIOutput_GetGammaControlCapabilities(IDXGIOutput *This, DXGI_GAMMA_CONTROL_CAPABILITIES * gamma_caps) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIOutput, 13};
    packet.args[0] = guest_address(gamma_caps);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIOutput_SetGammaControl(IDXGIOutput *This, const DXGI_GAMMA_CONTROL * gamma_control) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIOutput, 14};
    packet.args[0] = guest_address(gamma_control);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIOutput_GetGammaControl(IDXGIOutput *This, DXGI_GAMMA_CONTROL * gamma_control) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIOutput, 15};
    packet.args[0] = guest_address(gamma_control);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIOutput_SetDisplaySurface(IDXGIOutput *This, IDXGISurface * surface) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIOutput, 16};
    packet.args[0] = proxy_token(surface);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIOutput_GetDisplaySurfaceData(IDXGIOutput *This, IDXGISurface * surface) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIOutput, 17};
    packet.args[0] = proxy_token(surface);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIOutput_GetFrameStatistics(IDXGIOutput *This, DXGI_FRAME_STATISTICS * stats) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIOutput, 18};
    packet.args[0] = guest_address(stats);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static const IDXGIOutputVtbl vtbl_IDXGIOutput = {
    g_IDXGIOutput_QueryInterface,
    g_IDXGIOutput_AddRef,
    g_IDXGIOutput_Release,
    g_IDXGIOutput_SetPrivateData,
    g_IDXGIOutput_SetPrivateDataInterface,
    g_IDXGIOutput_GetPrivateData,
    g_IDXGIOutput_GetParent,
    g_IDXGIOutput_GetDesc,
    g_IDXGIOutput_GetDisplayModeList,
    g_IDXGIOutput_FindClosestMatchingMode,
    g_IDXGIOutput_WaitForVBlank,
    g_IDXGIOutput_TakeOwnership,
    g_IDXGIOutput_ReleaseOwnership,
    g_IDXGIOutput_GetGammaControlCapabilities,
    g_IDXGIOutput_SetGammaControl,
    g_IDXGIOutput_GetGammaControl,
    g_IDXGIOutput_SetDisplaySurface,
    g_IDXGIOutput_GetDisplaySurfaceData,
    g_IDXGIOutput_GetFrameStatistics
};
static HRESULT STDMETHODCALLTYPE g_IDXGIResource_QueryInterface(IDXGIResource *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_IDXGIResource_AddRef(IDXGIResource *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_IDXGIResource_Release(IDXGIResource *This) {
    return proxy_release(This);
}
static HRESULT STDMETHODCALLTYPE g_IDXGIResource_SetPrivateData(IDXGIResource *This, REFGUID guid, UINT data_size, const void * data) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIResource, 3};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)data_size;
    packet.args[2] = guest_address(data);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIResource_SetPrivateDataInterface(IDXGIResource *This, REFGUID guid, const IUnknown * object) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIResource, 4};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(object);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIResource_GetPrivateData(IDXGIResource *This, REFGUID guid, UINT * data_size, void * data) {
    return proxy_private_get(This, 5, guid, data_size, data);
}
static HRESULT STDMETHODCALLTYPE g_IDXGIResource_GetParent(IDXGIResource *This, REFIID riid, void ** parent) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIResource, 6};
    packet.args[0] = guest_address(riid);
    struct proxy_output wire_parent;
    if (!proxy_output_init(&wire_parent,parent,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_parent.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_parent,parent,safe_array_count(1),proxy_iid(riid))) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_parent,parent);
    proxy_output_dispose(&wire_parent,proxy_iid(riid));
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIResource_GetDevice(IDXGIResource *This, REFIID riid, void ** device) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIResource, 7};
    packet.args[0] = guest_address(riid);
    struct proxy_output wire_device;
    if (!proxy_output_init(&wire_device,device,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_device.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_device,device,safe_array_count(1),proxy_iid(riid))) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_device,device);
    proxy_output_dispose(&wire_device,proxy_iid(riid));
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIResource_GetSharedHandle(IDXGIResource *This, HANDLE * pSharedHandle) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIResource, 8};
    packet.args[0] = guest_address(pSharedHandle);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIResource_GetUsage(IDXGIResource *This, DXGI_USAGE * pUsage) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIResource, 9};
    packet.args[0] = guest_address(pUsage);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIResource_SetEvictionPriority(IDXGIResource *This, UINT EvictionPriority) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIResource, 10};
    packet.args[0] = (uint32_t)EvictionPriority;
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGIResource_GetEvictionPriority(IDXGIResource *This, UINT * pEvictionPriority) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGIResource, 11};
    packet.args[0] = guest_address(pEvictionPriority);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static const IDXGIResourceVtbl vtbl_IDXGIResource = {
    g_IDXGIResource_QueryInterface,
    g_IDXGIResource_AddRef,
    g_IDXGIResource_Release,
    g_IDXGIResource_SetPrivateData,
    g_IDXGIResource_SetPrivateDataInterface,
    g_IDXGIResource_GetPrivateData,
    g_IDXGIResource_GetParent,
    g_IDXGIResource_GetDevice,
    g_IDXGIResource_GetSharedHandle,
    g_IDXGIResource_GetUsage,
    g_IDXGIResource_SetEvictionPriority,
    g_IDXGIResource_GetEvictionPriority
};
static HRESULT STDMETHODCALLTYPE g_IDXGISurface_QueryInterface(IDXGISurface *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_IDXGISurface_AddRef(IDXGISurface *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_IDXGISurface_Release(IDXGISurface *This) {
    return proxy_release(This);
}
static HRESULT STDMETHODCALLTYPE g_IDXGISurface_SetPrivateData(IDXGISurface *This, REFGUID guid, UINT data_size, const void * data) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISurface, 3};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)data_size;
    packet.args[2] = guest_address(data);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISurface_SetPrivateDataInterface(IDXGISurface *This, REFGUID guid, const IUnknown * object) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISurface, 4};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(object);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISurface_GetPrivateData(IDXGISurface *This, REFGUID guid, UINT * data_size, void * data) {
    return proxy_private_get(This, 5, guid, data_size, data);
}
static HRESULT STDMETHODCALLTYPE g_IDXGISurface_GetParent(IDXGISurface *This, REFIID riid, void ** parent) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISurface, 6};
    packet.args[0] = guest_address(riid);
    struct proxy_output wire_parent;
    if (!proxy_output_init(&wire_parent,parent,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_parent.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_parent,parent,safe_array_count(1),proxy_iid(riid))) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_parent,parent);
    proxy_output_dispose(&wire_parent,proxy_iid(riid));
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISurface_GetDevice(IDXGISurface *This, REFIID riid, void ** device) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISurface, 7};
    packet.args[0] = guest_address(riid);
    struct proxy_output wire_device;
    if (!proxy_output_init(&wire_device,device,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_device.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_device,device,safe_array_count(1),proxy_iid(riid))) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_device,device);
    proxy_output_dispose(&wire_device,proxy_iid(riid));
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISurface_GetDesc(IDXGISurface *This, DXGI_SURFACE_DESC * desc) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISurface, 8};
    packet.args[0] = guest_address(desc);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISurface_Map(IDXGISurface *This, DXGI_MAPPED_RECT * mapped_rect, UINT flags) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISurface, 9};
    packet.args[0] = guest_address(mapped_rect);
    packet.args[1] = (uint32_t)flags;
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISurface_Unmap(IDXGISurface *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISurface, 10};
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static const IDXGISurfaceVtbl vtbl_IDXGISurface = {
    g_IDXGISurface_QueryInterface,
    g_IDXGISurface_AddRef,
    g_IDXGISurface_Release,
    g_IDXGISurface_SetPrivateData,
    g_IDXGISurface_SetPrivateDataInterface,
    g_IDXGISurface_GetPrivateData,
    g_IDXGISurface_GetParent,
    g_IDXGISurface_GetDevice,
    g_IDXGISurface_GetDesc,
    g_IDXGISurface_Map,
    g_IDXGISurface_Unmap
};
static HRESULT STDMETHODCALLTYPE g_IDXGISurface1_QueryInterface(IDXGISurface1 *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_IDXGISurface1_AddRef(IDXGISurface1 *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_IDXGISurface1_Release(IDXGISurface1 *This) {
    return proxy_release(This);
}
static HRESULT STDMETHODCALLTYPE g_IDXGISurface1_SetPrivateData(IDXGISurface1 *This, REFGUID guid, UINT data_size, const void * data) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISurface1, 3};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)data_size;
    packet.args[2] = guest_address(data);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISurface1_SetPrivateDataInterface(IDXGISurface1 *This, REFGUID guid, const IUnknown * object) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISurface1, 4};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(object);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISurface1_GetPrivateData(IDXGISurface1 *This, REFGUID guid, UINT * data_size, void * data) {
    return proxy_private_get(This, 5, guid, data_size, data);
}
static HRESULT STDMETHODCALLTYPE g_IDXGISurface1_GetParent(IDXGISurface1 *This, REFIID riid, void ** parent) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISurface1, 6};
    packet.args[0] = guest_address(riid);
    struct proxy_output wire_parent;
    if (!proxy_output_init(&wire_parent,parent,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_parent.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_parent,parent,safe_array_count(1),proxy_iid(riid))) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_parent,parent);
    proxy_output_dispose(&wire_parent,proxy_iid(riid));
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISurface1_GetDevice(IDXGISurface1 *This, REFIID riid, void ** device) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISurface1, 7};
    packet.args[0] = guest_address(riid);
    struct proxy_output wire_device;
    if (!proxy_output_init(&wire_device,device,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_device.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_device,device,safe_array_count(1),proxy_iid(riid))) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_device,device);
    proxy_output_dispose(&wire_device,proxy_iid(riid));
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISurface1_GetDesc(IDXGISurface1 *This, DXGI_SURFACE_DESC * desc) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISurface1, 8};
    packet.args[0] = guest_address(desc);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISurface1_Map(IDXGISurface1 *This, DXGI_MAPPED_RECT * mapped_rect, UINT flags) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISurface1, 9};
    packet.args[0] = guest_address(mapped_rect);
    packet.args[1] = (uint32_t)flags;
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISurface1_Unmap(IDXGISurface1 *This) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISurface1, 10};
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISurface1_GetDC(IDXGISurface1 *This, WINBOOL discard, HDC * hdc) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISurface1, 11};
    packet.args[0] = (uint32_t)discard;
    packet.args[1] = guest_address(hdc);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISurface1_ReleaseDC(IDXGISurface1 *This, RECT * dirty_rect) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISurface1, 12};
    packet.args[0] = guest_address(dirty_rect);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static const IDXGISurface1Vtbl vtbl_IDXGISurface1 = {
    g_IDXGISurface1_QueryInterface,
    g_IDXGISurface1_AddRef,
    g_IDXGISurface1_Release,
    g_IDXGISurface1_SetPrivateData,
    g_IDXGISurface1_SetPrivateDataInterface,
    g_IDXGISurface1_GetPrivateData,
    g_IDXGISurface1_GetParent,
    g_IDXGISurface1_GetDevice,
    g_IDXGISurface1_GetDesc,
    g_IDXGISurface1_Map,
    g_IDXGISurface1_Unmap,
    g_IDXGISurface1_GetDC,
    g_IDXGISurface1_ReleaseDC
};
static HRESULT STDMETHODCALLTYPE g_IDXGISwapChain_QueryInterface(IDXGISwapChain *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_IDXGISwapChain_AddRef(IDXGISwapChain *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_IDXGISwapChain_Release(IDXGISwapChain *This) {
    return proxy_release(This);
}
static HRESULT STDMETHODCALLTYPE g_IDXGISwapChain_SetPrivateData(IDXGISwapChain *This, REFGUID guid, UINT data_size, const void * data) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISwapChain, 3};
    packet.args[0] = guest_address(guid);
    packet.args[1] = (uint32_t)data_size;
    packet.args[2] = guest_address(data);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISwapChain_SetPrivateDataInterface(IDXGISwapChain *This, REFGUID guid, const IUnknown * object) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISwapChain, 4};
    packet.args[0] = guest_address(guid);
    packet.args[1] = proxy_token(object);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISwapChain_GetPrivateData(IDXGISwapChain *This, REFGUID guid, UINT * data_size, void * data) {
    return proxy_private_get(This, 5, guid, data_size, data);
}
static HRESULT STDMETHODCALLTYPE g_IDXGISwapChain_GetParent(IDXGISwapChain *This, REFIID riid, void ** parent) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISwapChain, 6};
    packet.args[0] = guest_address(riid);
    struct proxy_output wire_parent;
    if (!proxy_output_init(&wire_parent,parent,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_parent.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_parent,parent,safe_array_count(1),proxy_iid(riid))) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_parent,parent);
    proxy_output_dispose(&wire_parent,proxy_iid(riid));
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISwapChain_GetDevice(IDXGISwapChain *This, REFIID riid, void ** device) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISwapChain, 7};
    packet.args[0] = guest_address(riid);
    struct proxy_output wire_device;
    if (!proxy_output_init(&wire_device,device,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_device.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_device,device,safe_array_count(1),proxy_iid(riid))) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_device,device);
    proxy_output_dispose(&wire_device,proxy_iid(riid));
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISwapChain_Present(IDXGISwapChain *This, UINT sync_interval, UINT flags) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISwapChain, 8};
    packet.args[0] = (uint32_t)sync_interval;
    packet.args[1] = (uint32_t)flags;
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISwapChain_GetBuffer(IDXGISwapChain *This, UINT buffer_idx, REFIID riid, void ** surface) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISwapChain, 9};
    packet.args[0] = (uint32_t)buffer_idx;
    packet.args[1] = guest_address(riid);
    struct proxy_output wire_surface;
    if (!proxy_output_init(&wire_surface,surface,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[2] = guest_address(wire_surface.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_surface,surface,safe_array_count(1),proxy_iid(riid))) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_surface,surface);
    proxy_output_dispose(&wire_surface,proxy_iid(riid));
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISwapChain_SetFullscreenState(IDXGISwapChain *This, WINBOOL fullscreen, IDXGIOutput * target) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISwapChain, 10};
    packet.args[0] = (uint32_t)fullscreen;
    packet.args[1] = proxy_token(target);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISwapChain_GetFullscreenState(IDXGISwapChain *This, WINBOOL * fullscreen, IDXGIOutput ** target) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISwapChain, 11};
    packet.args[0] = guest_address(fullscreen);
    struct proxy_output wire_target;
    if (!proxy_output_init(&wire_target,target,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[1] = guest_address(wire_target.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_target,target,safe_array_count(1),SD_COM_IF_IDXGIOutput)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_target,target);
    proxy_output_dispose(&wire_target,SD_COM_IF_IDXGIOutput);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISwapChain_GetDesc(IDXGISwapChain *This, DXGI_SWAP_CHAIN_DESC * desc) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISwapChain, 12};
    packet.args[0] = guest_address(desc);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISwapChain_ResizeBuffers(IDXGISwapChain *This, UINT buffer_count, UINT width, UINT height, DXGI_FORMAT format, UINT flags) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISwapChain, 13};
    packet.args[0] = (uint32_t)buffer_count;
    packet.args[1] = (uint32_t)width;
    packet.args[2] = (uint32_t)height;
    packet.args[3] = (uint32_t)format;
    packet.args[4] = (uint32_t)flags;
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISwapChain_ResizeTarget(IDXGISwapChain *This, const DXGI_MODE_DESC * target_mode_desc) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISwapChain, 14};
    packet.args[0] = guest_address(target_mode_desc);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISwapChain_GetContainingOutput(IDXGISwapChain *This, IDXGIOutput ** output) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISwapChain, 15};
    struct proxy_output wire_output;
    if (!proxy_output_init(&wire_output,output,safe_array_count(1))) {  return (HRESULT)E_OUTOFMEMORY; }
    packet.args[0] = guest_address(wire_output.tokens);
    LONG status = proxy_call(&packet);
    if (status >= 0 && SUCCEEDED((HRESULT)packet.ret) && !proxy_output_publish(&wire_output,output,safe_array_count(1),SD_COM_IF_IDXGIOutput)) status=E_OUTOFMEMORY;
    if (!(status >= 0 && SUCCEEDED((HRESULT)packet.ret))) proxy_output_retract(&wire_output,output);
    proxy_output_dispose(&wire_output,SD_COM_IF_IDXGIOutput);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISwapChain_GetFrameStatistics(IDXGISwapChain *This, DXGI_FRAME_STATISTICS * stats) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISwapChain, 16};
    packet.args[0] = guest_address(stats);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static HRESULT STDMETHODCALLTYPE g_IDXGISwapChain_GetLastPresentCount(IDXGISwapChain *This, UINT * last_present_count) {
    struct sd_com_packet packet = {SD_COM_ABI, proxy_token(This), SD_COM_IF_IDXGISwapChain, 17};
    packet.args[0] = guest_address(last_present_count);
    LONG status = proxy_call(&packet);
    if (status < 0) { return (HRESULT)status; }
    return (HRESULT)packet.ret;
}
static const IDXGISwapChainVtbl vtbl_IDXGISwapChain = {
    g_IDXGISwapChain_QueryInterface,
    g_IDXGISwapChain_AddRef,
    g_IDXGISwapChain_Release,
    g_IDXGISwapChain_SetPrivateData,
    g_IDXGISwapChain_SetPrivateDataInterface,
    g_IDXGISwapChain_GetPrivateData,
    g_IDXGISwapChain_GetParent,
    g_IDXGISwapChain_GetDevice,
    g_IDXGISwapChain_Present,
    g_IDXGISwapChain_GetBuffer,
    g_IDXGISwapChain_SetFullscreenState,
    g_IDXGISwapChain_GetFullscreenState,
    g_IDXGISwapChain_GetDesc,
    g_IDXGISwapChain_ResizeBuffers,
    g_IDXGISwapChain_ResizeTarget,
    g_IDXGISwapChain_GetContainingOutput,
    g_IDXGISwapChain_GetFrameStatistics,
    g_IDXGISwapChain_GetLastPresentCount
};
static HRESULT STDMETHODCALLTYPE g_IUnknown_QueryInterface(IUnknown *This, REFIID riid, void ** ppvObject) {
    return proxy_query(This, riid, ppvObject);
}
static ULONG STDMETHODCALLTYPE g_IUnknown_AddRef(IUnknown *This) {
    return proxy_addref(This);
}
static ULONG STDMETHODCALLTYPE g_IUnknown_Release(IUnknown *This) {
    return proxy_release(This);
}
static const IUnknownVtbl vtbl_IUnknown = {
    g_IUnknown_QueryInterface,
    g_IUnknown_AddRef,
    g_IUnknown_Release
};
static const void *proxy_vtable(uint32_t interface_id) {
    switch (interface_id) {
    case SD_COM_IF_ID3D10Multithread: return &vtbl_ID3D10Multithread;
    case SD_COM_IF_ID3D11Asynchronous: return &vtbl_ID3D11Asynchronous;
    case SD_COM_IF_ID3D11BlendState: return &vtbl_ID3D11BlendState;
    case SD_COM_IF_ID3D11Buffer: return &vtbl_ID3D11Buffer;
    case SD_COM_IF_ID3D11ClassInstance: return &vtbl_ID3D11ClassInstance;
    case SD_COM_IF_ID3D11ClassLinkage: return &vtbl_ID3D11ClassLinkage;
    case SD_COM_IF_ID3D11CommandList: return &vtbl_ID3D11CommandList;
    case SD_COM_IF_ID3D11ComputeShader: return &vtbl_ID3D11ComputeShader;
    case SD_COM_IF_ID3D11Counter: return &vtbl_ID3D11Counter;
    case SD_COM_IF_ID3D11DepthStencilState: return &vtbl_ID3D11DepthStencilState;
    case SD_COM_IF_ID3D11DepthStencilView: return &vtbl_ID3D11DepthStencilView;
    case SD_COM_IF_ID3D11Device: return &vtbl_ID3D11Device;
    case SD_COM_IF_ID3D11DeviceChild: return &vtbl_ID3D11DeviceChild;
    case SD_COM_IF_ID3D11DeviceContext: return &vtbl_ID3D11DeviceContext;
    case SD_COM_IF_ID3D11DomainShader: return &vtbl_ID3D11DomainShader;
    case SD_COM_IF_ID3D11GeometryShader: return &vtbl_ID3D11GeometryShader;
    case SD_COM_IF_ID3D11HullShader: return &vtbl_ID3D11HullShader;
    case SD_COM_IF_ID3D11InputLayout: return &vtbl_ID3D11InputLayout;
    case SD_COM_IF_ID3D11PixelShader: return &vtbl_ID3D11PixelShader;
    case SD_COM_IF_ID3D11Predicate: return &vtbl_ID3D11Predicate;
    case SD_COM_IF_ID3D11Query: return &vtbl_ID3D11Query;
    case SD_COM_IF_ID3D11RasterizerState: return &vtbl_ID3D11RasterizerState;
    case SD_COM_IF_ID3D11RenderTargetView: return &vtbl_ID3D11RenderTargetView;
    case SD_COM_IF_ID3D11Resource: return &vtbl_ID3D11Resource;
    case SD_COM_IF_ID3D11SamplerState: return &vtbl_ID3D11SamplerState;
    case SD_COM_IF_ID3D11ShaderResourceView: return &vtbl_ID3D11ShaderResourceView;
    case SD_COM_IF_ID3D11Texture1D: return &vtbl_ID3D11Texture1D;
    case SD_COM_IF_ID3D11Texture2D: return &vtbl_ID3D11Texture2D;
    case SD_COM_IF_ID3D11Texture3D: return &vtbl_ID3D11Texture3D;
    case SD_COM_IF_ID3D11UnorderedAccessView: return &vtbl_ID3D11UnorderedAccessView;
    case SD_COM_IF_ID3D11VertexShader: return &vtbl_ID3D11VertexShader;
    case SD_COM_IF_ID3D11View: return &vtbl_ID3D11View;
    case SD_COM_IF_IDXGIAdapter: return &vtbl_IDXGIAdapter;
    case SD_COM_IF_IDXGIAdapter1: return &vtbl_IDXGIAdapter1;
    case SD_COM_IF_IDXGIDevice: return &vtbl_IDXGIDevice;
    case SD_COM_IF_IDXGIDevice1: return &vtbl_IDXGIDevice1;
    case SD_COM_IF_IDXGIDeviceSubObject: return &vtbl_IDXGIDeviceSubObject;
    case SD_COM_IF_IDXGIFactory: return &vtbl_IDXGIFactory;
    case SD_COM_IF_IDXGIFactory1: return &vtbl_IDXGIFactory1;
    case SD_COM_IF_IDXGIKeyedMutex: return &vtbl_IDXGIKeyedMutex;
    case SD_COM_IF_IDXGIObject: return &vtbl_IDXGIObject;
    case SD_COM_IF_IDXGIOutput: return &vtbl_IDXGIOutput;
    case SD_COM_IF_IDXGIResource: return &vtbl_IDXGIResource;
    case SD_COM_IF_IDXGISurface: return &vtbl_IDXGISurface;
    case SD_COM_IF_IDXGISurface1: return &vtbl_IDXGISurface1;
    case SD_COM_IF_IDXGISwapChain: return &vtbl_IDXGISwapChain;
    case SD_COM_IF_IUnknown: return &vtbl_IUnknown;
    default: return NULL;
    }
}
