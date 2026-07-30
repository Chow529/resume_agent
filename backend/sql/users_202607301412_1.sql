-- dmmdb.users 定义

CREATE TABLE `users` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `username` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户名',
  `email` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '邮箱',
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '加密后的密码（使用 bcrypt/argon2）',
  `salt` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '加盐值（如使用非默认算法）',
  `is_active` tinyint(1) DEFAULT '1' COMMENT '账户状态（1=激活，0=禁用）',
  `failed_login_attempts` tinyint DEFAULT '0' COMMENT '失败登录次数',
  `last_failed_login_at` timestamp NULL DEFAULT NULL COMMENT '上次失败登录时间',
  `is_locked` tinyint(1) DEFAULT '0' COMMENT '是否被锁定（超过失败次数）',
  `password_last_changed_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改密码时间',
  `last_login_at` timestamp NULL DEFAULT NULL COMMENT '上次登录时间',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`),
  KEY `idx_username` (`username`),
  KEY `idx_email` (`email`),
  KEY `idx_status` (`is_active`,`is_locked`),
  KEY `idx_failed_attempts` (`failed_login_attempts`,`is_locked`),
  KEY `idx_password_changed` (`password_last_changed_at`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;