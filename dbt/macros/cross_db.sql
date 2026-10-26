{#- SQL that runs unchanged on DuckDB (dev) and BigQuery (hosted). Engine-specific bits live here. -#}

{% macro week_start(col) -%}
  {%- if target.type == 'bigquery' -%} date_trunc(cast({{ col }} as date), week(monday))
  {%- else -%} cast(date_trunc('week', cast({{ col }} as date)) as date)
  {%- endif -%}
{%- endmacro %}

{% macro safe_divide(num, den) -%}
  ({{ num }}) / nullif(({{ den }}), 0)
{%- endmacro %}

{% macro median(col) -%}
  {%- if target.type == 'bigquery' -%} approx_quantiles({{ col }}, 100)[offset(50)]
  {%- else -%} median({{ col }})
  {%- endif -%}
{%- endmacro %}

{% macro to_ts(col) -%}
  {%- if target.type == 'bigquery' -%} cast({{ col }} as datetime)
  {%- else -%} cast({{ col }} as timestamp)
  {%- endif -%}
{%- endmacro %}

{% macro float_type() -%}
  {%- if target.type == 'bigquery' -%} float64 {%- else -%} double {%- endif -%}
{%- endmacro %}

{# Name the schemas exactly as configured (staging / intermediate / marts), no target prefix. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
  {%- if custom_schema_name is none -%} {{ target.schema }}
  {%- elif target.type == 'bigquery' -%} {{ target.schema }}_{{ custom_schema_name | trim }}
  {%- else -%} {{ custom_schema_name | trim }}
  {%- endif -%}
{%- endmacro %}
