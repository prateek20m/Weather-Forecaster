from datetime import datetime
import pyowm
import streamlit as st
from matplotlib import pyplot as plt
from matplotlib import dates as mdates
import pytz   # for IST timezone conversion

# Load API key securely
owm_key = st.secrets["API_KEY"]
owm = pyowm.OWM(owm_key)
weather_mgr = owm.weather_manager()

deg_sign = u"\N{DEGREE SIGN}"

# ------------------------- HELPERS ------------------------- #
@st.cache_data(show_spinner=False)
def load_weather(city_name, temp_unit):
    obs = weather_mgr.weather_at_place(city_name)
    now_weather = obs.weather
    forecast_obj = weather_mgr.forecast_at_place(city_name, "3h")
    return now_weather, forecast_obj, forecast_obj.forecast


def extract_temp_trend(forecast, unit="celsius"):
    daily_min, daily_max, days = {}, {}, []
    for f in forecast:
        d = datetime.utcfromtimestamp(f.reference_time()).date()
        temp_val = f.temperature(unit=unit)['temp']
        if d not in daily_min:
            days.append(d)
            daily_min[d] = temp_val
            daily_max[d] = temp_val
        else:
            daily_min[d] = min(daily_min[d], temp_val)
            daily_max[d] = max(daily_max[d], temp_val)
    return days, [daily_min[d] for d in days], [daily_max[d] for d in days]


def extract_humidity(forecast):
    humidity_map, days = {}, []
    for f in forecast:
        d = datetime.utcfromtimestamp(f.reference_time()).date()
        if d not in humidity_map:
            days.append(d)
            humidity_map[d] = f.humidity
        else:
            humidity_map[d] = max(humidity_map[d], f.humidity)
    return days, [humidity_map[d] for d in days]


def extract_wind_speed(forecast):
    wind_map, days = {}, []
    for f in forecast:
        d = datetime.utcfromtimestamp(f.reference_time()).date()
        wind_speed = f.wind()['speed']
        if d not in wind_map:
            days.append(d)
            wind_map[d] = wind_speed
        else:
            wind_map[d] = max(wind_map[d], wind_speed)
    return days, [wind_map[d] for d in days]


# ------------------------- PLOTTING ------------------------- #
def show_temp_chart(forecast, chart_type, unit="celsius"):
    days, tmin, tmax = extract_temp_trend(forecast, unit)
    days_num = mdates.date2num(days)

    fig, ax = plt.subplots()
    ax.set_title("🌤️ 5-Day Temperature Overview")
    ax.set_xlabel("Date")
    ax.set_ylabel(f"Temperature ({deg_sign}{'C' if unit=='celsius' else 'F'})")

    if chart_type == "Bar Graph":
        ax.bar(days_num - 0.2, tmin, width=0.4, color="#1f77b4", label="Min")
        ax.bar(days_num + 0.2, tmax, width=0.4, color="#ff7f0e", label="Max")
    else:
        ax.plot(days_num, tmin, "-o", color="#1f77b4", label="Min")
        ax.plot(days_num, tmax, "-o", color="#ff7f0e", label="Max")

    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
    return fig


def show_humidity_chart(forecast):
    days, hum = extract_humidity(forecast)
    days_num = mdates.date2num(days)

    fig, ax = plt.subplots()
    ax.set_title("💧 Humidity Trend (5 Days)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Humidity (%)")

    ax.bar(days_num, hum, color="#00bfff")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
    return fig


def show_wind_chart(forecast):
    days, winds = extract_wind_speed(forecast)
    days_num = mdates.date2num(days)

    fig, ax = plt.subplots()
    ax.set_title("🌬️ Wind Speed Forecast (5 Days)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Wind Speed (m/s)")

    ax.plot(days_num, winds, "-s", color="#228B22", label="Max Wind Speed")
    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
    return fig


# ------------------------- DISPLAY ------------------------- #
def display_current_weather(weather, unit="celsius"):
    icon_url = weather.weather_icon_url(size="4x")  # size can be 2x, 4x, etc.
    st.image(icon_url, caption=weather.detailed_status.title())
    temp = weather.temperature(unit=unit)['temp']
    feels = weather.temperature(unit=unit)['feels_like']

    st.subheader(f"🌡️ {round(temp)}{deg_sign}{'C' if unit=='celsius' else 'F'} (Feels like {round(feels)}{deg_sign})")
    st.write(f"☁️ Clouds: {weather.clouds}%")
    st.write(f"💨 Wind: {weather.wind()['speed']} m/s")
    st.write(f"💧 Humidity: {weather.humidity}%")
    st.write(f"⏲️ Pressure: {weather.pressure['press']} mBar")
    st.write(f"🛣️ Visibility: {weather.visibility(unit='kilometers')} km")


def display_alerts(forecaster):
    st.markdown("### ⚠️ Weather Alerts")
    alerts = []
    if forecaster.will_have_rain(): alerts.append("Rain Expected 🌧️")
    if forecaster.will_have_snow(): alerts.append("Snowfall ❄️")
    if forecaster.will_have_storm(): alerts.append("Storm Alert ⛈️")
    if forecaster.will_have_fog(): alerts.append("Foggy 🌫️")
    if not alerts:
        st.success("No unusual weather predicted! ✅")
    else:
        for a in alerts:
            st.warning(a)


def display_sun_times(weather):
    ist = pytz.timezone("Asia/Kolkata")   # IST timezone

    sr = datetime.fromtimestamp(int(weather.sunrise_time()), tz=pytz.utc).astimezone(ist)
    ss = datetime.fromtimestamp(int(weather.sunset_time()), tz=pytz.utc).astimezone(ist)

    st.markdown("### 🌅 Sunrise & Sunset (IST)")
    st.write(f"Sunrise: {sr.strftime('%I:%M %p')} ({sr.date()})")
    st.write(f"Sunset: {ss.strftime('%I:%M %p')} ({ss.date()})")


# ------------------------- MAIN ------------------------- #
st.title("Weather-Forecaster 🌤 ️")
st.caption("Forecast tool by **Prateek**")

cities_input = st.text_input("Enter Cities (comma-separated, 1 or 2):",    value="",  # start empty
    placeholder="Enter city names here")
unit_choice = st.radio("Temperature Unit:", ["celsius", "fahrenheit"])
chart_type = st.radio("Chart Type:", ["Bar Graph", "Line Graph"])

if st.button("Show Forecast"):
    cities = [c.strip() for c in cities_input.split(",")][:2]  # Limit to 2 cities
    if not cities:
        st.error("⚠️ Please enter at least one city name.")
    else:
        cols = st.columns(len(cities))  # Side-by-side display

        for idx, city in enumerate(cities):
            with cols[idx]:
                st.subheader(f"🏙️ {city}")
                try:
                    current, forecaster, forecast_list = load_weather(city, unit_choice)
                    display_current_weather(current, unit_choice)
                    st.pyplot(show_temp_chart(forecast_list, chart_type, unit_choice))
                    display_alerts(forecaster)
                    display_sun_times(current)
                    st.pyplot(show_humidity_chart(forecast_list))
                    st.pyplot(show_wind_chart(forecast_list))
                except Exception as err:
                    st.error(f"Could not fetch data for {city}: {err}")
