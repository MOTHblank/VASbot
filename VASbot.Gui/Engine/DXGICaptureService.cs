using System;
using System.Drawing;
using System.Runtime.InteropServices;
using Vortice.Direct3D11;
using Vortice.DXGI;
using SkiaSharp;

namespace VASbot.Gui.Engine
{
    public class DXGICaptureService : IDisposable
    {
        private ID3D11Device? _device;
        private ID3D11DeviceContext? _deviceContext;
        private IDXGIOutputDuplication? _deskDupl;
        private ID3D11Texture2D? _stagingTexture;
        private bool _isInitialized = false;

        public DXGICaptureService()
        {
            InitializeDirectX();
        }

        private void InitializeDirectX()
        {
            try
            {
                var result = D3D11.D3D11CreateDevice(null, Vortice.Direct3D.DriverType.Hardware, DeviceCreationFlags.None, null!, out _device, out _deviceContext);
                if (result.Failure || _device == null) return;

                using var dxgiDevice = _device.QueryInterface<IDXGIDevice>();
                using var adapter = dxgiDevice.GetAdapter();
                if (adapter.EnumOutputs(0, out var output).Failure) return;
                
                using var output1 = output.QueryInterface<IDXGIOutput1>();
                _deskDupl = output1.DuplicateOutput(_device);
                _isInitialized = true;
            }
            catch { _isInitialized = false; }
        }

        public SKBitmap? Capture(Rectangle rect)
        {
            if (!_isInitialized || _deskDupl == null || _deviceContext == null || _device == null) 
            {
                InitializeDirectX();
                return null;
            }

            try
            {
                var result = _deskDupl.AcquireNextFrame(50, out _, out var resource);
                if (result.Failure) return null;

                using var texture = resource.QueryInterface<ID3D11Texture2D>();
                var desc = texture.Description;

                if (_stagingTexture == null || _stagingTexture.Description.Width != desc.Width || _stagingTexture.Description.Height != desc.Height)
                {
                    _stagingTexture?.Dispose();
                    _stagingTexture = _device.CreateTexture2D(new Texture2DDescription
                    {
                        Width = desc.Width,
                        Height = desc.Height,
                        MipLevels = 1,
                        ArraySize = 1,
                        Format = desc.Format,
                        SampleDescription = new SampleDescription(1, 0),
                        Usage = ResourceUsage.Staging,
                        BindFlags = BindFlags.None,
                        CPUAccessFlags = CpuAccessFlags.Read
                    });
                }

                _deviceContext.CopyResource(_stagingTexture, texture);
                _deskDupl.ReleaseFrame();

                var mapped = _deviceContext.Map(_stagingTexture, 0, MapMode.Read, Vortice.Direct3D11.MapFlags.None);
                
                var info = new SKImageInfo((int)desc.Width, (int)desc.Height, SKColorType.Bgra8888, SKAlphaType.Premul);
                
                // CRITICAL: We must COPY the pixels. InstallPixels is just a pointer.
                var tempBitmap = new SKBitmap();
                tempBitmap.InstallPixels(info, mapped.DataPointer, (int)mapped.RowPitch);
                
                SKBitmap finalBitmap;
                if (rect.Width > 0 && rect.Height > 0)
                {
                    // Crop creates a copy naturally
                    finalBitmap = new SKBitmap(rect.Width, rect.Height);
                    tempBitmap.ExtractSubset(finalBitmap, new SKRectI(rect.Left, rect.Top, rect.Right, rect.Bottom));
                }
                else
                {
                    // Explicit copy of the whole bitmap
                    finalBitmap = tempBitmap.Copy();
                }

                tempBitmap.Dispose();
                _deviceContext.Unmap(_stagingTexture, 0);

                return finalBitmap;
            }
            catch
            {
                _isInitialized = false;
                return null;
            }
        }

        public void Dispose()
        {
            _stagingTexture?.Dispose();
            _deskDupl?.Dispose();
            _deviceContext?.Dispose();
            _device?.Dispose();
        }
    }
}
