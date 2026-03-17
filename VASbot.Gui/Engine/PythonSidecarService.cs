using System;
using System.Diagnostics;
using System.IO;
using System.Threading.Tasks;

namespace VASbot.Gui.Engine
{
    public class PythonSidecarService : IDisposable
    {
        private Process? _sidecarProcess;
        private readonly string _pythonPath = "python";
        private bool _isIntentionalStop = false;

        public event Action<string>? OutputReceived;
        public event Action<bool>? StateChanged;

        public bool IsRunning => _sidecarProcess != null && !_sidecarProcess.HasExited;

        public void Start()
        {
            if (IsRunning) return;
            _isIntentionalStop = false;

            try
            {
                string appRoot = AppDomain.CurrentDomain.BaseDirectory;
                string pythonDir = Path.GetFullPath(Path.Combine(appRoot, "..", "..", "..", "..", "python"));
                string scriptPath = Path.Combine(pythonDir, "bot_runner.py");

                if (!File.Exists(scriptPath))
                {
                    OutputReceived?.Invoke($"[Sidecar] ERROR: Script not found at {scriptPath}");
                    return;
                }

                ProcessStartInfo startInfo = new ProcessStartInfo
                {
                    FileName = _pythonPath,
                    Arguments = $"-u \"{scriptPath}\"",
                    WorkingDirectory = pythonDir,
                    UseShellExecute = false, 
                    CreateNoWindow = true,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true
                };

                _sidecarProcess = new Process { StartInfo = startInfo };
                _sidecarProcess.EnableRaisingEvents = true;
                
                _sidecarProcess.OutputDataReceived += (s, e) => {
                    if (e.Data != null) OutputReceived?.Invoke(e.Data);
                };
                _sidecarProcess.ErrorDataReceived += (s, e) => {
                    if (e.Data != null) OutputReceived?.Invoke($"[PYTHON ERR] {e.Data}");
                };
                _sidecarProcess.Exited += async (s, e) => {
                    StateChanged?.Invoke(false);
                    OutputReceived?.Invoke("[Sidecar] Process exited.");

                    if (!_isIntentionalStop)
                    {
                        OutputReceived?.Invoke("[Sidecar] Crash detected. Attempting to auto-restart in 3 seconds...");
                        await Task.Delay(3000);
                        if (!_isIntentionalStop)
                        {
                            Start();
                        }
                    }
                };

                _sidecarProcess.Start();
                _sidecarProcess.BeginOutputReadLine();
                _sidecarProcess.BeginErrorReadLine();

                StateChanged?.Invoke(true);
                OutputReceived?.Invoke($"[Sidecar] Started (PID: {_sidecarProcess.Id})");
            }
            catch (Exception ex)
            {
                OutputReceived?.Invoke($"[Sidecar] Start Failed: {ex.Message}");
            }
        }

        public void Stop()
        {
            _isIntentionalStop = true;
            if (IsRunning)
            {
                try
                {
                    _sidecarProcess?.Kill();
                    _sidecarProcess?.Dispose();
                    _sidecarProcess = null;
                    StateChanged?.Invoke(false);
                    OutputReceived?.Invoke("[Sidecar] Stopped.");
                }
                catch { }
            }
        }

        public void Dispose()
        {
            Stop();
        }
    }
}
