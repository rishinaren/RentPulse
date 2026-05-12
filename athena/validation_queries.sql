-- name: raw_record_counts
select
    dataset_name,
    count(*) as record_count,
    max(from_iso8601_timestamp(ingested_at)) as latest_ingested_at
from ${glue_database}.${raw_table}
group by dataset_name;

-- name: required_dataset_presence
select
    count(distinct dataset_name) as loaded_dataset_count
from ${glue_database}.${raw_table}
where dataset_name in (
    'zillow_zori_zip',
    'zillow_inventory_zip',
    'nyc_housing_units_by_building',
    'nyc_dob_approved_permits',
    'mta_subway_stations',
    'listing_snapshots'
);

-- name: duplicate_record_hashes
-- Same logical row re-ingested in a later run shares record_hash; only flag duplicates within one run_id.
select
    dataset_name,
    record_hash,
    run_id,
    count(*) as duplicate_count
from ${glue_database}.${raw_table}
group by dataset_name, record_hash, run_id
having count(*) > 1
limit 100;

-- name: listing_snapshot_price_quality
select
    count(*) as invalid_listing_rent_count
from ${glue_database}.${raw_table}
where dataset_name = 'listing_snapshots'
  and try_cast(payload['rent'] as double) is null;
