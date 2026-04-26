local function normalize_category(category)
    if not category or category == "" then
        return "unknown"
    end

    local normalized = string.lower(category)
    normalized = string.gsub(normalized, "-", "_")
    normalized = string.gsub(normalized, "%s+", "_")

    local aliases = {
        food_court = "fast_food",
        ice_cream = "cafe",
        coffee_shop = "cafe",
        club = "nightclub",
    }

    return aliases[normalized] or normalized
end

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
    record["category"] = normalize_category(record["category"])
    record["merchant_type"] = record["category"]
    record["txn_count"] = 1
    record["total_volume_eur"] = tonumber(record["amount"]) or 0

    return 1, timestamp, record
end
