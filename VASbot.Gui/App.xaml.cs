using System.Windows;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using VASbot.Gui.Engine;
using VASbot.Gui.UI.ViewModels;
using System;
using System.IO;

namespace VASbot.Gui
{
    public partial class App : Application
    {
        public static IHost? AppHost { get; private set; }

        public App()
        {
            try
            {
                AppHost = Host.CreateDefaultBuilder()
                    .ConfigureServices((hostContext, services) =>
                    {
                        // --- Core Engine Services ---
                        services.AddSingleton<SharedMemoryService>();
                        services.AddSingleton<ScreenshotService>();
                        services.AddSingleton<PythonSidecarService>();
                        services.AddSingleton<DXGICaptureService>();
                        services.AddSingleton<UIAutomationService>();
                        services.AddSingleton<TemplateService>();
                        services.AddSingleton<RegionManager>();
                        services.AddSingleton<CoordinateTransformer>();
                        services.AddSingleton<ReflectionService>();
                        
                        // --- Bot Infrastructure ---
                        services.AddSingleton<IBotService>(sp => 
                            BotServiceFactory.CreateGrpc("http://localhost:50051", sp.GetRequiredService<ScreenshotService>()));

                                            // --- ViewModels ---
                                            services.AddSingleton<ScriptEditorViewModel>();
                                            services.AddSingleton<CaptureViewModel>();
                                            services.AddSingleton<AutomationTreeViewModel>();
                                            services.AddSingleton<TemplateViewModel>();
                                            services.AddSingleton<HotkeySettingsViewModel>();
                                            services.AddSingleton<InspectorViewModel>();
                                            services.AddSingleton<SidecarViewModel>();
                                            services.AddSingleton<VisualEditorViewModel>();
                                            services.AddSingleton<MainViewModel>();
                                                // --- Window ---
                        services.AddSingleton<MainWindow>();
                    })
                    .Build();
            }
            catch (Exception ex)
            {
                LogFatalError("Constructor", ex);
                throw;
            }
        }

        protected override async void OnStartup(StartupEventArgs e)
        {
            try
            {
                if (AppHost == null) throw new Exception("AppHost is null during OnStartup.");

                await AppHost.StartAsync();

                var mainWindow = AppHost.Services.GetRequiredService<MainWindow>();
                if (mainWindow == null) throw new Exception("Failed to resolve MainWindow from DI.");

                mainWindow.Show();
            }
            catch (Exception ex)
            {
                LogFatalError("OnStartup", ex);
                MessageBox.Show($"FATAL STARTUP ERROR:\n{ex.Message}\n\nCheck startup_error.txt for details.");
                Shutdown();
            }

            base.OnStartup(e);
        }

        private void LogFatalError(string stage, Exception ex)
        {
            string logPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "startup_error.txt");
            string message = $"[{DateTime.Now}] FATAL ERROR in {stage}:\n{ex}\n\n";
            File.AppendAllText(logPath, message);
        }

        protected override async void OnExit(ExitEventArgs e)
        {
            if (AppHost != null)
            {
                await AppHost.StopAsync();
                AppHost.Dispose();
            }
            base.OnExit(e);
        }
    }
}
