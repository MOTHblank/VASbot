using System;
using System.Windows;
using VASbot.Gui.Engine;
using VASbot.Gui.UI.ViewModels;
using System.Windows;
using VASbot.Gui.Engine;
using VASbot.Gui.UI.ViewModels;
using System.Globalization;
using System.Windows.Data;

namespace VASbot.Gui.UI.Converters
{
    public class EnumValuesConverter : IValueConverter
    {
        public object Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
        {
            if (value is Type type && type.IsEnum)
            {
                return Enum.GetValues(type)!;
            }
            return null!;
        }

        public object ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }
}
