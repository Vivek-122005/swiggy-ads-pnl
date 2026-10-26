select zone_id, zone_name, lat, lon from {{ ref('stg_zones') }}
