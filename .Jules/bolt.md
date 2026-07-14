## $(date +%Y-%m-%d) - Optimize BitBlt screenshot conversion
**Learning:** In C# when converting from `System.Drawing.Bitmap` to `SkiaSharp.SKBitmap`, using `MemoryStream` to save and re-decode an image is very slow and allocation-heavy. `VASbot.Gui` allows `unsafe` code.
**Action:** Use `Bitmap.LockBits` and a direct `Buffer.MemoryCopy` with `BitmapData.Scan0` to bypass encoding/decoding overhead. This is a critical codebase-specific performance pattern for any C# graphics interop.
## $(date +%Y-%m-%d) - Optimize SKBitmap Pixel Access
**Learning:** In C#, using `SKBitmap.GetPixel(x, y)` inside a tight rendering loop is incredibly slow due to virtual method overhead and per-pixel bounds checking. The `VASbot.Gui` allows `unsafe` blocks.
**Action:** Always replace nested loops using `GetPixel(x, y)` on `SKBitmap` with direct memory pointer access (`unsafe` block + `GetPixels().ToPointer()`). Always validate `BytesPerPixel` (e.g., `== 4`) before performing pointer arithmetic.
## 2026-07-06 - Optimize numpy color matching with cv2.inRange
**Learning:** In Python/NumPy, doing a manual element-wise absolute difference and  comparison () is significantly slower (around 5x) than using OpenCV's native C++ implementation  for masking ranges, even when considering the minimal overhead of preparing the bounds array.
**Action:** When finding specific colors within a region in computer vision, use  in place of NumPy arithmetic when OpenCV is available to drastically improve speed, especially when performed frequently.
## $(date +%Y-%m-%d) - Optimize numpy color matching with cv2.inRange
**Learning:** In Python/NumPy, doing a manual element-wise absolute difference and `np.all` comparison (`np.where(np.all(np.abs(roi - target) <= tolerance, axis=2))`) is significantly slower (around 5x) than using OpenCV's native C++ implementation `cv2.inRange()` for masking ranges, even when considering the minimal overhead of preparing the bounds array.
**Action:** When finding specific colors within a region in computer vision, use `cv2.inRange()` in place of NumPy arithmetic when OpenCV is available to drastically improve speed, especially when performed frequently.
## 2026-07-06 - Cache numpy arrays for high-frequency OpenCV bounds
**Learning:** In high-frequency vision loops (like `find_color`), constructing `np.array` boundary definitions over and over for `cv2.inRange` introduces significant and unnecessary memory allocation overhead when checking for the same target colors.
**Action:** Use `@lru_cache` to memoize the creation of these bounding numpy arrays based on the color tuple and tolerance values. This completely bypasses repetitive `np.array` instantiation overhead in tight computer vision loops.
## 2026-07-10 - Optimize color bound arrays for cv2.inRange
**Learning:** In Python/NumPy computer vision scripts, creating bounding array objects via `np.array(...)` in high-frequency tight vision loops (like `find_color` and `find_color_clusters`) creates unnecessary overhead and frequent memory allocations that degrade performance.
**Action:** When generating `lower` and `upper` boundary arrays for `cv2.inRange` based on color ranges, cache the generated arrays in a dictionary keyed by `(color_value, tolerance, has_alpha)` to reuse them without reallocation.
## $(date +%Y-%m-%d) - Optimize batch array construction in Python loops
**Learning:** In Python, repeatedly calling `.append()` inside a loop to construct an array (e.g., generating `Input` structs for Windows API) introduces significant interpreter overhead per iteration, especially for long sequences of text.
**Action:** When constructing arrays dynamically without interleaved delays, use list comprehensions (or generators) rather than repeated `.append()` calls. It avoids method lookup overhead and allows the C-backend list builder to pre-allocate memory more efficiently.
## 2024-05-24 - [Optimize Non-Maximum Suppression (NMS)]
**Learning:** Pure Python nested loops for filtering overlapping bounding boxes via Non-Maximum Suppression (NMS) creates an O(N^2) performance bottleneck during template matching. OpenCV's `cv2.dnn.NMSBoxes` provides a highly optimized native C++ implementation that runs significantly (~40x) faster.
**Action:** Replace manual NMS loops with `cv2.dnn.NMSBoxes` to improve bounding box filtering performance.
