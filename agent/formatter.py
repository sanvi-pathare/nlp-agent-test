import json

def flatten_dict(item, parent_key=""):
    flat = {}
    if isinstance(item, dict):
        for key, value in item.items():
            new_key = f"{parent_key}.{key}" if parent_key else key
            flat.update(flatten_dict(value, new_key))
    else:
        flat[parent_key] = item
    return flat

def build_markdown_table(headers, rows):
    header_line = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    lines = [header_line, separator]
    for row in rows:
        cells = []
        for h in headers:
            val = row.get(h, "")
            val_str = str(val).replace("|", "\\|")
            cells.append(val_str)
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)

def get_singular_noun(api):
    api_id = api.get("id", "")
    if "host" in api_id.lower():
        return "Host"
    if "profile" in api_id.lower():
        return "Profile"
    if "agent" in api_id.lower():
        return "Agent"
    if "param" in api_id.lower():
        return "Parameter"
    return "Key"

def format_api_response(api, raw_response):
    """
    Generic dynamic formatter for API responses.
    Returns a formatted string (table or list) if it should be displayed as a table,
    otherwise returns None to fallback to natural language explanation.
    """
    # 1. Parse JSON
    try:
        payload = json.loads(raw_response)
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None

    if not payload.get("success"):
        return None

    data = payload.get("data")
    if data is None or data == "" or data == [] or data == {}:
        return None

    # Only format GET requests as tables
    method = api.get("method", "GET").upper()
    if method != "GET":
        return None

    # 2. Extract primary list if data is a dict with a single list key
    if isinstance(data, dict) and len(data) == 1:
        key = list(data.keys())[0]
        if isinstance(data[key], list):
            data = data[key]

    # 3. Format different structures
    # Structure A: List of items
    if isinstance(data, list):
        if not data:
            return None
            
        all_keys = set()
        rows = []
        for item in data:
            if isinstance(item, dict):
                flat_item = flatten_dict(item)
                rows.append(flat_item)
                all_keys.update(flat_item.keys())
            else:
                singular = get_singular_noun(api)
                rows.append({singular: item})
                all_keys.add(singular)

        if not rows:
            return None

        # Priority keys mapping to match case-insensitive
        priority = ["name", "id", "status", "type", "profile", "host", "value", "agent", "server"]
        def key_priority(k):
            k_low = k.lower()
            for idx, pk in enumerate(priority):
                if k_low == pk or k_low.endswith("." + pk) or k_low.startswith(pk + "."):
                    return idx
            return len(priority)

        ordered_keys = sorted(list(all_keys), key=lambda k: (key_priority(k), k.lower()))

        # Determine plural noun for the message
        noun = get_singular_noun(api)
        plural_noun = noun + "s" if not noun.endswith("s") else noun
        if noun.lower() == "host":
            plural_noun = "hosts"

        # Dynamically decide formatting:
        # If columns <= 4, show single consolidated table
        if len(ordered_keys) <= 4:
            table_str = build_markdown_table(ordered_keys, rows)
            count = len(rows)
            item_word = noun.lower() if count == 1 else plural_noun.lower()
            return f"Found {count} {item_word}:\n\n{table_str}"
        else:
            # Show a separate vertical table for each item
            primary_key = ordered_keys[0]
            other_keys = [k for k in ordered_keys if k != primary_key]

            blocks = []
            for row in rows:
                title_val = row.get(primary_key, "Item")
                block_lines = [
                    f"**{primary_key}: {title_val}**",
                    "",
                    "| Property | Value |",
                    "| :--- | :--- |"
                ]
                for k in other_keys:
                    val = row.get(k, "")
                    if val is None or val == "":
                        continue
                    if isinstance(val, (dict, list)):
                        val_str = json.dumps(val, ensure_ascii=False)
                    else:
                        val_str = str(val)
                    val_escaped = val_str.replace("|", "\\|")
                    block_lines.append(f"| {k} | {val_escaped} |")
                blocks.append("\n".join(block_lines))
            
            count = len(rows)
            item_word = noun.lower() if count == 1 else plural_noun.lower()
            return f"Found {count} {item_word}:\n\n" + "\n\n".join(blocks)

    # Structure B: Dictionary where all values are dictionaries
    if isinstance(data, dict) and all(isinstance(v, dict) for v in data.values()):
        rows = []
        key_header = get_singular_noun(api)
        for k, v in data.items():
            row = {key_header: k}
            row.update(flatten_dict(v))
            rows.append(row)

        all_keys = set()
        for r in rows:
            all_keys.update(r.keys())

        priority = ["name", "id", "status", "type", "profile", "host", "value", "agent", "server"]
        def key_priority(k):
            k_low = k.lower()
            for idx, pk in enumerate(priority):
                if k_low == pk or k_low.endswith("." + pk) or k_low.startswith(pk + "."):
                    return idx
            return len(priority)

        ordered_keys = sorted(list(all_keys), key=lambda k: (key_priority(k), k.lower()))

        noun = get_singular_noun(api)
        plural_noun = noun + "s" if not noun.endswith("s") else noun

        if len(ordered_keys) <= 4:
            table_str = build_markdown_table(ordered_keys, rows)
            count = len(rows)
            item_word = noun.lower() if count == 1 else plural_noun.lower()
            return f"Found {count} {item_word}:\n\n{table_str}"
        else:
            primary_key = ordered_keys[0]
            other_keys = [k for k in ordered_keys if k != primary_key]

            blocks = []
            for row in rows:
                title_val = row.get(primary_key, "Item")
                block_lines = [
                    f"**{primary_key}: {title_val}**",
                    "",
                    "| Property | Value |",
                    "| :--- | :--- |"
                ]
                for k in other_keys:
                    val = row.get(k, "")
                    if val is None or val == "":
                        continue
                    if isinstance(val, (dict, list)):
                        val_str = json.dumps(val, ensure_ascii=False)
                    else:
                        val_str = str(val)
                    val_escaped = val_str.replace("|", "\\|")
                    block_lines.append(f"| {k} | {val_escaped} |")
                blocks.append("\n".join(block_lines))
            
            count = len(rows)
            item_word = noun.lower() if count == 1 else plural_noun.lower()
            return f"Found {count} {item_word}:\n\n" + "\n\n".join(blocks)

    # Structure C: Flat dictionary (Key-Value pairs)
    if isinstance(data, dict) and all(not isinstance(v, (dict, list)) for v in data.values()):
        rows = []
        for k, v in sorted(data.items()):
            rows.append({"Parameter": k, "Value": str(v)})
        table_str = build_markdown_table(["Parameter", "Value"], rows)
        count = len(data)
        return f"Found {count} parameters:\n\n{table_str}"

    return None
