function cb_filter(tag, timestamp, record)
    if not record["merchant_id"] or record["merchant_id"] == "" then
        return 2, 0, {}
    end
    if not record["amount"] or tonumber(record["amount"]) == nil then
        return 2, 0, {}
    end

    local ts = timestamp
    if type(ts) == "table" then ts = ts["sec"] or 0 end
    local t = os.date("*t", ts)
    local dow = (t.wday + 5) % 7

    record["hour_of_day"] = t.hour
    record["day_of_week"] = dow
    record["hour_of_week"] = dow * 24 + t.hour
    record["merchant_type"] = record["category"] or "unknown"
    record["txn_count"] = 1
    record["total_volume_eur"] = tonumber(record["amount"]) or 0

    return 1, timestamp, record
end
