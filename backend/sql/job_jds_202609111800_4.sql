-- job_jds 定义（与线上库结构核对一致）
-- 岗位 JD 数据表：存储用户通过采集模块（智联招聘等）爬取到的岗位 JD
--
-- 设计说明：
-- 1. user_id 为数据所有者；is_public=1 时该条数据对所有用户可见（公用数据）。
-- 2. source 标识数据来源模块（如 zhaopin=智联招聘），后续新增采集模块时复用本表，
--    模块特有字段统一放入 raw_json，无需改动表结构。
-- 3. (user_id, source, source_job_id) 唯一，同一用户重复爬取同一岗位时走
--    INSERT ... ON DUPLICATE KEY UPDATE，避免产生重复数据。

CREATE TABLE `job_jds` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id` int unsigned NOT NULL COMMENT '数据所属用户ID',
  `source` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'zhaopin' COMMENT '采集来源模块：zhaopin=智联招聘',
  `source_job_id` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '来源站点的岗位ID（用于去重）',
  `job_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '岗位名称',
  `company_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '公司名称',
  `salary` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '薪资',
  `city` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '工作城市',
  `district` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '所在区域',
  `education` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '学历要求',
  `experience` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '经验要求',
  `company_size` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '公司规模',
  `industry` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '公司行业',
  `financing_stage` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '融资阶段',
  `skill_tags` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '技能标签',
  `welfare` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '福利',
  `labels` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '商业/其他标签',
  `keyword` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '爬取时使用的搜索关键词',
  `job_url` varchar(1000) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '岗位详情页URL',
  `jd_content` mediumtext COLLATE utf8mb4_unicode_ci COMMENT 'JD文本内容（结构化字段拼装，供面试提问使用）',
  `raw_json` mediumtext COLLATE utf8mb4_unicode_ci COMMENT '采集到的原始完整数据（JSON，含模块特有字段）',
  `is_public` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否公用数据：0=个人私有，1=公用（公用后不可改回私有）',
  `use_count` int NOT NULL DEFAULT '0' COMMENT '被选为面试目标岗位的次数（个人/公用排名依据）',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_source_job` (`user_id`,`source`,`source_job_id`),
  KEY `idx_user_public` (`user_id`,`is_public`),
  KEY `idx_public` (`is_public`),
  KEY `idx_source_job` (`source`,`source_job_id`),
  KEY `idx_use_count` (`use_count`),
  CONSTRAINT `job_jds_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='岗位JD数据表（个人+公用）';
