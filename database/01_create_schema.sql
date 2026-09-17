-- Run while connected to zed_real_estate_analytics. MariaDB has one database namespace.

CREATE TABLE IF NOT EXISTS etl_load_batch (
  load_batch_id BIGINT NOT NULL AUTO_INCREMENT, source_system ENUM('CRM','Meta','Manual') NOT NULL,
  source_file_name VARCHAR(260), started_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at_utc DATETIME, status ENUM('Started','Completed','CompletedWithErrors','Failed') NOT NULL DEFAULT 'Started',
  rows_read INT NOT NULL DEFAULT 0, rows_loaded INT NOT NULL DEFAULT 0, rows_rejected INT NOT NULL DEFAULT 0,
  PRIMARY KEY (load_batch_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS etl_rejected_record (
  rejected_record_id BIGINT NOT NULL AUTO_INCREMENT, load_batch_id BIGINT NOT NULL, source_row_number INT,
  entity_name VARCHAR(50) NOT NULL, error_message VARCHAR(1000) NOT NULL, raw_payload LONGTEXT,
  rejected_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (rejected_record_id),
  CONSTRAINT fk_rejected_record_batch FOREIGN KEY (load_batch_id) REFERENCES etl_load_batch(load_batch_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS dim_date (
  date_key INT NOT NULL, calendar_date DATE NOT NULL, calendar_year SMALLINT NOT NULL, calendar_quarter TINYINT NOT NULL,
  calendar_month TINYINT NOT NULL, month_name VARCHAR(12) NOT NULL, week_of_year TINYINT NOT NULL,
  day_of_month TINYINT NOT NULL, day_of_week TINYINT NOT NULL, day_name VARCHAR(12) NOT NULL, is_weekend TINYINT(1) NOT NULL,
  PRIMARY KEY (date_key), UNIQUE KEY uq_date_calendar_date (calendar_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS dim_platform (
  platform_key INT NOT NULL AUTO_INCREMENT, platform_name ENUM('Facebook','Instagram') NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1, PRIMARY KEY (platform_key), UNIQUE KEY uq_platform_name (platform_name)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS dim_agent (
  agent_key INT NOT NULL AUTO_INCREMENT, source_agent_id VARCHAR(50) NOT NULL, agent_name VARCHAR(150) NOT NULL,
  email VARCHAR(254), is_active TINYINT(1) NOT NULL DEFAULT 1, created_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (agent_key), UNIQUE KEY uq_agent_source_id (source_agent_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS dim_property (
  property_key INT NOT NULL AUTO_INCREMENT, source_property_id VARCHAR(50) NOT NULL,
  property_type ENUM('House','Apartment','Townhouse','Unit','Land','Commercial') NOT NULL, suburb VARCHAR(100) NOT NULL,
  state_code CHAR(3) NOT NULL DEFAULT 'VIC', postcode VARCHAR(10), bedrooms TINYINT, listing_price DECIMAL(14,2),
  is_active TINYINT(1) NOT NULL DEFAULT 1, PRIMARY KEY (property_key), UNIQUE KEY uq_property_source_id (source_property_id),
  CONSTRAINT ck_property_bedrooms CHECK (bedrooms IS NULL OR bedrooms BETWEEN 0 AND 20),
  CONSTRAINT ck_property_price CHECK (listing_price IS NULL OR listing_price >= 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS dim_campaign (
  campaign_key INT NOT NULL AUTO_INCREMENT, source_campaign_id VARCHAR(100) NOT NULL, campaign_name VARCHAR(200) NOT NULL,
  platform_key INT NOT NULL, start_date_key INT, end_date_key INT, objective VARCHAR(50), is_active TINYINT(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (campaign_key), UNIQUE KEY uq_campaign_source_id (source_campaign_id),
  CONSTRAINT fk_campaign_platform FOREIGN KEY (platform_key) REFERENCES dim_platform(platform_key),
  CONSTRAINT fk_campaign_start_date FOREIGN KEY (start_date_key) REFERENCES dim_date(date_key),
  CONSTRAINT fk_campaign_end_date FOREIGN KEY (end_date_key) REFERENCES dim_date(date_key),
  CONSTRAINT ck_campaign_dates CHECK (end_date_key IS NULL OR start_date_key IS NULL OR end_date_key >= start_date_key)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS dim_post (
  post_key BIGINT NOT NULL AUTO_INCREMENT, source_post_id VARCHAR(100) NOT NULL, platform_key INT NOT NULL,
  campaign_key INT, property_key INT, published_date_key INT NOT NULL, published_time TIME NOT NULL,
  post_type ENUM('Image','Video','Carousel','Story','Reel','Link','Other') NOT NULL, post_caption VARCHAR(2000), post_url VARCHAR(2048),
  PRIMARY KEY (post_key), UNIQUE KEY uq_post_source_id (source_post_id),
  CONSTRAINT fk_post_platform FOREIGN KEY (platform_key) REFERENCES dim_platform(platform_key),
  CONSTRAINT fk_post_campaign FOREIGN KEY (campaign_key) REFERENCES dim_campaign(campaign_key),
  CONSTRAINT fk_post_property FOREIGN KEY (property_key) REFERENCES dim_property(property_key),
  CONSTRAINT fk_post_date FOREIGN KEY (published_date_key) REFERENCES dim_date(date_key)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS fact_post_performance_daily (
  post_performance_daily_key BIGINT NOT NULL AUTO_INCREMENT, post_key BIGINT NOT NULL, date_key INT NOT NULL,
  impressions INT NOT NULL DEFAULT 0, reach INT NOT NULL DEFAULT 0, link_clicks INT NOT NULL DEFAULT 0,
  reactions INT NOT NULL DEFAULT 0, comments INT NOT NULL DEFAULT 0, shares INT NOT NULL DEFAULT 0, saves INT NOT NULL DEFAULT 0,
  ad_spend DECIMAL(12,2) NOT NULL DEFAULT 0, load_batch_id BIGINT,
  PRIMARY KEY (post_performance_daily_key), UNIQUE KEY uq_post_performance_post_date (post_key,date_key), KEY ix_post_performance_date (date_key,post_key),
  CONSTRAINT fk_performance_post FOREIGN KEY (post_key) REFERENCES dim_post(post_key),
  CONSTRAINT fk_performance_date FOREIGN KEY (date_key) REFERENCES dim_date(date_key),
  CONSTRAINT fk_performance_batch FOREIGN KEY (load_batch_id) REFERENCES etl_load_batch(load_batch_id),
  CONSTRAINT ck_performance_values CHECK (impressions >= 0 AND reach >= 0 AND link_clicks >= 0 AND reactions >= 0 AND comments >= 0 AND shares >= 0 AND saves >= 0 AND ad_spend >= 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS fact_lead (
  lead_key BIGINT NOT NULL AUTO_INCREMENT, source_lead_id VARCHAR(100) NOT NULL, enquiry_date_key INT NOT NULL,
  inspection_date_key INT, conversion_date_key INT, platform_key INT, campaign_key INT, post_key BIGINT, property_key INT, agent_key INT,
  lead_status ENUM('Enquiry','InspectionBooked','Converted','Lost') NOT NULL, conversion_type ENUM('Sale','Lease'), revenue_amount DECIMAL(14,2),
  load_batch_id BIGINT, created_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (lead_key), UNIQUE KEY uq_lead_source_id (source_lead_id), KEY ix_lead_agent_date (agent_key,enquiry_date_key), KEY ix_lead_campaign_date (campaign_key,enquiry_date_key),
  CONSTRAINT fk_lead_enquiry_date FOREIGN KEY (enquiry_date_key) REFERENCES dim_date(date_key), CONSTRAINT fk_lead_inspection_date FOREIGN KEY (inspection_date_key) REFERENCES dim_date(date_key), CONSTRAINT fk_lead_conversion_date FOREIGN KEY (conversion_date_key) REFERENCES dim_date(date_key),
  CONSTRAINT fk_lead_platform FOREIGN KEY (platform_key) REFERENCES dim_platform(platform_key), CONSTRAINT fk_lead_campaign FOREIGN KEY (campaign_key) REFERENCES dim_campaign(campaign_key), CONSTRAINT fk_lead_post FOREIGN KEY (post_key) REFERENCES dim_post(post_key), CONSTRAINT fk_lead_property FOREIGN KEY (property_key) REFERENCES dim_property(property_key), CONSTRAINT fk_lead_agent FOREIGN KEY (agent_key) REFERENCES dim_agent(agent_key), CONSTRAINT fk_lead_batch FOREIGN KEY (load_batch_id) REFERENCES etl_load_batch(load_batch_id),
  CONSTRAINT ck_lead_chronology CHECK ((inspection_date_key IS NULL OR inspection_date_key >= enquiry_date_key) AND (conversion_date_key IS NULL OR conversion_date_key >= enquiry_date_key)),
  CONSTRAINT ck_lead_conversion CHECK ((lead_status = 'Converted' AND conversion_date_key IS NOT NULL AND conversion_type IS NOT NULL AND revenue_amount >= 0) OR (lead_status <> 'Converted' AND conversion_date_key IS NULL AND conversion_type IS NULL AND revenue_amount IS NULL))
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS stg_crm_lead (
  staging_crm_lead_id BIGINT NOT NULL AUTO_INCREMENT, load_batch_id BIGINT NOT NULL, source_row_number INT, source_lead_id VARCHAR(100),
  enquiry_date_text VARCHAR(50), inspection_date_text VARCHAR(50), conversion_date_text VARCHAR(50), agent_id_text VARCHAR(50), property_id_text VARCHAR(50), campaign_id_text VARCHAR(100), post_id_text VARCHAR(100), lead_status_text VARCHAR(50), conversion_type_text VARCHAR(50), revenue_text VARCHAR(50), is_processed TINYINT(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (staging_crm_lead_id), CONSTRAINT fk_stg_crm_batch FOREIGN KEY (load_batch_id) REFERENCES etl_load_batch(load_batch_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS stg_meta_post_performance (
  staging_meta_post_performance_id BIGINT NOT NULL AUTO_INCREMENT, load_batch_id BIGINT NOT NULL, source_row_number INT, source_post_id VARCHAR(100), report_date_text VARCHAR(50), impressions_text VARCHAR(50), reach_text VARCHAR(50), link_clicks_text VARCHAR(50), reactions_text VARCHAR(50), comments_text VARCHAR(50), shares_text VARCHAR(50), saves_text VARCHAR(50), ad_spend_text VARCHAR(50), is_processed TINYINT(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (staging_meta_post_performance_id), CONSTRAINT fk_stg_meta_batch FOREIGN KEY (load_batch_id) REFERENCES etl_load_batch(load_batch_id)
) ENGINE=InnoDB;
