/* Generated type compatibility. */
static bool interface_is_a(uint32_t actual, uint32_t expected) {
    if (actual == expected) return true;
    switch (actual) {
    case SD_COM_IF_ID3D10Multithread: return expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11Asynchronous: return expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11BlendState: return expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11Buffer: return expected == SD_COM_IF_ID3D11Resource || expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11ClassInstance: return expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11ClassLinkage: return expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11CommandList: return expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11ComputeShader: return expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11Counter: return expected == SD_COM_IF_ID3D11Asynchronous || expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11DepthStencilState: return expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11DepthStencilView: return expected == SD_COM_IF_ID3D11View || expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11Device: return expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11DeviceChild: return expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11DeviceContext: return expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11DomainShader: return expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11GeometryShader: return expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11HullShader: return expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11InputLayout: return expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11PixelShader: return expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11Predicate: return expected == SD_COM_IF_ID3D11Query || expected == SD_COM_IF_ID3D11Asynchronous || expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11Query: return expected == SD_COM_IF_ID3D11Asynchronous || expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11RasterizerState: return expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11RenderTargetView: return expected == SD_COM_IF_ID3D11View || expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11Resource: return expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11SamplerState: return expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11ShaderResourceView: return expected == SD_COM_IF_ID3D11View || expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11Texture1D: return expected == SD_COM_IF_ID3D11Resource || expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11Texture2D: return expected == SD_COM_IF_ID3D11Resource || expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11Texture3D: return expected == SD_COM_IF_ID3D11Resource || expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11UnorderedAccessView: return expected == SD_COM_IF_ID3D11View || expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11VertexShader: return expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_ID3D11View: return expected == SD_COM_IF_ID3D11DeviceChild || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_IDXGIAdapter: return expected == SD_COM_IF_IDXGIObject || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_IDXGIAdapter1: return expected == SD_COM_IF_IDXGIAdapter || expected == SD_COM_IF_IDXGIObject || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_IDXGIDevice: return expected == SD_COM_IF_IDXGIObject || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_IDXGIDevice1: return expected == SD_COM_IF_IDXGIDevice || expected == SD_COM_IF_IDXGIObject || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_IDXGIDeviceSubObject: return expected == SD_COM_IF_IDXGIObject || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_IDXGIFactory: return expected == SD_COM_IF_IDXGIObject || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_IDXGIFactory1: return expected == SD_COM_IF_IDXGIFactory || expected == SD_COM_IF_IDXGIObject || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_IDXGIKeyedMutex: return expected == SD_COM_IF_IDXGIDeviceSubObject || expected == SD_COM_IF_IDXGIObject || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_IDXGIObject: return expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_IDXGIOutput: return expected == SD_COM_IF_IDXGIObject || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_IDXGIResource: return expected == SD_COM_IF_IDXGIDeviceSubObject || expected == SD_COM_IF_IDXGIObject || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_IDXGISurface: return expected == SD_COM_IF_IDXGIDeviceSubObject || expected == SD_COM_IF_IDXGIObject || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_IDXGISurface1: return expected == SD_COM_IF_IDXGISurface || expected == SD_COM_IF_IDXGIDeviceSubObject || expected == SD_COM_IF_IDXGIObject || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_IDXGISwapChain: return expected == SD_COM_IF_IDXGIDeviceSubObject || expected == SD_COM_IF_IDXGIObject || expected == SD_COM_IF_IUnknown;
    case SD_COM_IF_IUnknown: return false;
    default: return false;
    }
}
