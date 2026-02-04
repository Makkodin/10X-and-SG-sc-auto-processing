import pandas as pd
from datetime import datetime, timedelta

def check_flowcells_by_date(df, date_column='flowcell', max_days_diff=2):

    unique_flowcells = df[date_column].dropna().unique()

    flowcell_dates = {}
    valid_flowcells = []
    
    for flowcell in unique_flowcells:
        if isinstance(flowcell, str) and len(flowcell) >= 6:
            date_str = flowcell[:6]
            try:
                date = datetime.strptime(date_str, '%y%m%d')
                flowcell_dates[flowcell] = date
            except ValueError:
                continue 
    if len(flowcell_dates) < 2:
        return list(flowcell_dates.keys())
    dates_list = list(flowcell_dates.values())
    min_date = min(dates_list)
    max_date = max(dates_list)

    days_diff = (max_date - min_date).days
    
    if days_diff <= max_days_diff:
        valid_flowcells = list(flowcell_dates.keys())
    else:
        date_groups = {}
        for flowcell, date in flowcell_dates.items():
            date_key = date.strftime('%y%m%d')
            if date_key not in date_groups:
                date_groups[date_key] = []
            date_groups[date_key].append(flowcell)

        largest_group = max(date_groups.values(), key=len)
        main_date_str = [k for k, v in date_groups.items() if v == largest_group][0]
        main_date = datetime.strptime(main_date_str, '%y%m%d')
 
        for flowcell, date in flowcell_dates.items():
            if abs((date - main_date).days) <= max_days_diff:
                valid_flowcells.append(flowcell)
    
    return valid_flowcells

