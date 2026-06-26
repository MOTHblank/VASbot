using System;
using System.Windows;
using VASbot.Gui.Engine;
using VASbot.Gui.UI.ViewModels;
using System.IO.MemoryMappedFiles;
using SkiaSharp;
using System.Drawing;

namespace VASbot.Gui.Engine
{
    public class SharedMemoryService : IDisposable
    {
        private const string MapName = "VASbot_FrameBuffer";
        private const int MaxFrameSize = 1920 * 1080 * 4; // Full HD BGRA
        
        private MemoryMappedFile? _mmf;
        private MemoryMappedViewAccessor? _accessor;
        
        public string Name => MapName;

        public SharedMemoryService()
        {
            Initialize();
        }

        private void Initialize()
        {
            try
            {
                // Create or open the memory mapped file
                _mmf = MemoryMappedFile.CreateOrOpen(MapName, MaxFrameSize, MemoryMappedFileAccess.ReadWrite);
                _accessor = _mmf.CreateViewAccessor(0, MaxFrameSize, MemoryMappedFileAccess.Write);
                Console.WriteLine($"[SharedMemory] Initialized map: {MapName}");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[SharedMemory] Failed to initialize: {ex.Message}");
            }
        }

        public unsafe void WriteFrame(SKBitmap bitmap)
        {
            if (_accessor == null || bitmap == null) return;

            int size = bitmap.RowBytes * bitmap.Height;
            if (size > MaxFrameSize) return;

            // Get pointer to the memory
            byte* ptr = null;
            _accessor.SafeMemoryMappedViewHandle.AcquirePointer(ref ptr);
            try
            {
                // Fast memory copy directly from SkiaSharp pointer to Shared Memory
                Buffer.MemoryCopy(
                    (void*)bitmap.GetPixels(), 
                    ptr, 
                    MaxFrameSize, 
                    size
                );
            }
            finally
            {
                _accessor.SafeMemoryMappedViewHandle.ReleasePointer();
            }
        }

        public void Dispose()
        {
            _accessor?.Dispose();
            _mmf?.Dispose();
        }
    }
}
