from datetime import datetime, timedelta

def get_period_range(period: str):

    end_date = datetime.utcnow()

    if period == "week":
        start_date = end_date - timedelta(days=7)

    else:
        start_date = end_date - timedelta(days=7)

    return start_date, end_date