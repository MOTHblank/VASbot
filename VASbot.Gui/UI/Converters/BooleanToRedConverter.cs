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
                return new SolidColorBrush((System.Windows.Media.Color)System.Windows.Media.ColorConverter.ConvertFromString("#c0392b"));
            }
            return new SolidColorBrush(System.Windows.Media.Color.FromArgb(0, 0, 0, 0)); // Transparent
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }
}
