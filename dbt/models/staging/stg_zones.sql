select
    cast(zone_id as {{ dbt.type_string() }})   as zone_id,
    cast(zone_name as {{ dbt.type_string() }}) as zone_name,
    cast(lat as {{ float_type() }})            as lat,
    cast(lon as {{ float_type() }})            as lon
from {{ source('raw', 'raw_zones') }}
