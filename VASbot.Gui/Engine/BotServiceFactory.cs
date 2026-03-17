using System;
using VASbot.Gui.Engine;

namespace VASbot.Gui.Engine
{
    public static class BotServiceFactory
    {
        public static IBotService CreateGrpc(string address, ScreenshotService screenshotService)
        {
            return new GrpcBotService(address, screenshotService);
        }

        public static IBotService CreateRemote(string address)
        {
            throw new NotImplementedException("Generic remote services not implemented yet.");
        }
        
        public static IBotService CreatePipe(string pipeName)
        {
            throw new NotImplementedException("Named Pipe services not implemented yet.");
        }
    }
}
