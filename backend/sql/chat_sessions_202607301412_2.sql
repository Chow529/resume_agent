-- chat_sessions 定义（与线上库结构核对一致）

CREATE TABLE `chat_sessions` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '会话ID',
  `user_id` int unsigned NOT NULL COMMENT '用户ID',
  `session_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '会话名称',
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'initialized' COMMENT '面试状态：initialized=未开始面试，interviewing=面试中，terminated=已结束',
  `question_count` int NOT NULL DEFAULT '0' COMMENT '当前面试轮次',
  `selected_jd_id` int unsigned DEFAULT NULL COMMENT '本次面试选择的目标岗位JD ID（job_jds.id）',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_selected_jd_id` (`selected_jd_id`),
  CONSTRAINT `user_id_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
