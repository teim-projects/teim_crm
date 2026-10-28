from dateutil.relativedelta import relativedelta


def generate_service_dates(start_date, end_date, frequency_months):
    """
    Generate planned AMC service dates between start and end date
    based on frequency (in months).
    """

    service_dates = []
    current_date = start_date

    while current_date <= end_date:
        service_dates.append(current_date)
        current_date = current_date + relativedelta(
            months=frequency_months
        )

    return service_dates


import math

def distance_km(lat1, lon1, lat2, lon2):
    R = 6371

    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c