USE zed_real_estate_analytics;

CREATE OR REPLACE VIEW rpt_post_performance AS
SELECT d.calendar_date AS report_date,p.source_post_id,p.post_type,p.published_time,platform.platform_name,c.source_campaign_id,c.campaign_name,property_dim.source_property_id,property_dim.property_type,property_dim.suburb,f.impressions,f.reach,f.link_clicks,f.reactions,f.comments,f.shares,f.saves,f.ad_spend,
 CAST(CASE WHEN f.impressions=0 THEN 0 ELSE 100.0*f.link_clicks/f.impressions END AS DECIMAL(9,2)) AS click_through_rate_pct,
 CAST(CASE WHEN f.reach=0 THEN 0 ELSE 100.0*(f.reactions+f.comments+f.shares+f.saves)/f.reach END AS DECIMAL(9,2)) AS engagement_rate_pct
FROM fact_post_performance_daily f JOIN dim_post p ON p.post_key=f.post_key JOIN dim_date d ON d.date_key=f.date_key JOIN dim_platform platform ON platform.platform_key=p.platform_key LEFT JOIN dim_campaign c ON c.campaign_key=p.campaign_key LEFT JOIN dim_property property_dim ON property_dim.property_key=p.property_key;

CREATE OR REPLACE VIEW rpt_lead_funnel AS
SELECT enquiry.calendar_date AS enquiry_date,platform.platform_name,campaign.campaign_name,property_dim.property_type,property_dim.suburb,agent.agent_name,
 COUNT(*) AS enquiries,SUM(l.inspection_date_key IS NOT NULL) AS inspections_booked,SUM(l.conversion_date_key IS NOT NULL) AS conversions,SUM(l.conversion_type='Sale') AS sales,SUM(l.conversion_type='Lease') AS leases,SUM(COALESCE(l.revenue_amount,0)) AS conversion_value
FROM fact_lead l JOIN dim_date enquiry ON enquiry.date_key=l.enquiry_date_key LEFT JOIN dim_platform platform ON platform.platform_key=l.platform_key LEFT JOIN dim_campaign campaign ON campaign.campaign_key=l.campaign_key LEFT JOIN dim_property property_dim ON property_dim.property_key=l.property_key LEFT JOIN dim_agent agent ON agent.agent_key=l.agent_key
GROUP BY enquiry.calendar_date,platform.platform_name,campaign.campaign_name,property_dim.property_type,property_dim.suburb,agent.agent_name;

CREATE OR REPLACE VIEW rpt_campaign_performance AS
WITH daily_media AS (
 SELECT d.calendar_date AS report_date,platform.platform_name,c.campaign_key,c.source_campaign_id,c.campaign_name,SUM(f.impressions) AS impressions,SUM(f.reach) AS reach,SUM(f.link_clicks) AS link_clicks,SUM(f.ad_spend) AS ad_spend
 FROM fact_post_performance_daily f JOIN dim_post p ON p.post_key=f.post_key JOIN dim_date d ON d.date_key=f.date_key JOIN dim_platform platform ON platform.platform_key=p.platform_key LEFT JOIN dim_campaign c ON c.campaign_key=p.campaign_key
 GROUP BY d.calendar_date,platform.platform_name,c.campaign_key,c.source_campaign_id,c.campaign_name
), daily_leads AS (
 SELECT l.campaign_key,d.calendar_date AS enquiry_date,COUNT(*) AS leads,SUM(l.conversion_date_key IS NOT NULL) AS conversions FROM fact_lead l JOIN dim_date d ON d.date_key=l.enquiry_date_key GROUP BY l.campaign_key,d.calendar_date
)
SELECT m.report_date,m.platform_name,m.source_campaign_id,m.campaign_name,m.impressions,m.reach,m.link_clicks,m.ad_spend,COALESCE(l.leads,0) AS leads,COALESCE(l.conversions,0) AS conversions,CAST(CASE WHEN COALESCE(l.leads,0)=0 THEN NULL ELSE m.ad_spend/l.leads END AS DECIMAL(12,2)) AS cost_per_lead
FROM daily_media m LEFT JOIN daily_leads l ON l.campaign_key=m.campaign_key AND l.enquiry_date=m.report_date;
