USE zed_real_estate_analytics;

-- Finished batches where the recorded total does not reconcile.
SELECT load_batch_id,source_system,rows_read,rows_loaded,rows_rejected,status FROM etl_load_batch WHERE status IN ('Completed','CompletedWithErrors') AND rows_read <> rows_loaded+rows_rejected;

-- Leads with an invalid conversion state.
SELECT source_lead_id,lead_status,conversion_date_key,conversion_type,revenue_amount FROM fact_lead WHERE (lead_status='Converted' AND (conversion_date_key IS NULL OR conversion_type IS NULL OR revenue_amount IS NULL)) OR (lead_status<>'Converted' AND conversion_date_key IS NOT NULL);

-- Posts whose platform disagrees with their campaign.
SELECT p.source_post_id,post_platform.platform_name AS post_platform,campaign_platform.platform_name AS campaign_platform FROM dim_post p JOIN dim_platform post_platform ON post_platform.platform_key=p.platform_key JOIN dim_campaign c ON c.campaign_key=p.campaign_key JOIN dim_platform campaign_platform ON campaign_platform.platform_key=c.platform_key WHERE p.platform_key<>c.platform_key;

-- Unresolved staging records in completed batches.
SELECT b.load_batch_id,b.source_system,b.status,(SELECT COUNT(*) FROM stg_crm_lead c WHERE c.load_batch_id=b.load_batch_id AND c.is_processed=0)+(SELECT COUNT(*) FROM stg_meta_post_performance m WHERE m.load_batch_id=b.load_batch_id AND m.is_processed=0) AS unprocessed_rows FROM etl_load_batch b WHERE b.status IN ('Completed','CompletedWithErrors') HAVING unprocessed_rows>0;
