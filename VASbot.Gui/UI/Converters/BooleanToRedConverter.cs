using System;
using System.Globalization;
using System.Windows.Data;
using System.Windows.Media;

namespace VASbot.Gui.UI.Converters
{
    public class BooleanToRedConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (value is bool isRecording && isRecording)
            {
                return new SolidColorBrush(Color.FromRgb(231, 76, 60)); // Red
            }
            return new SolidColorBrush(Color.FromRgb(45, 45, 45)); // Default dark
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }
}
