// Generated from contracts/openapi.json. Do not edit.
export interface paths {
    "/api/v1/account": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Account */
        get: operations["get_account"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/account/ledger": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Ledger */
        get: operations["list_ledger"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/agents": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Admin Agents */
        get: operations["admin_agents"];
        put?: never;
        /** Publish Agent */
        post: operations["publish_agent"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/audit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Audit */
        get: operations["admin_list_audit"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/audit/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Summary Audit */
        get: operations["admin_audit_summary"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/content-access-grants": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Content Grants */
        get: operations["admin_list_content_grants"];
        put?: never;
        /** Content Grants */
        post: operations["admin_grant_content_access"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/content-access-grants/{id}/revoke": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Revoke Grant */
        post: operations["admin_revoke_content_grant"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/content/{resource_type}/{id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Content */
        get: operations["admin_read_content"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/content/{resource_type}/{id}/download": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Download */
        get: operations["admin_download_content"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/credit-grants": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Credit Grants */
        post: operations["admin_grant_credits"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/investigation-alerts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Alerts */
        get: operations["list_investigation_alerts"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/investigations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Investigations */
        get: operations["list_investigations"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/investigations/{task_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Investigation */
        get: operations["get_investigation"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/investigations/{task_id}/assign": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Assign */
        post: operations["assign_investigation"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/ledger": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Platform Ledger */
        get: operations["admin_list_ledger"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/ledger/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Summary Ledger */
        get: operations["admin_ledger_summary"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/managed-users": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Users */
        get: operations["admin_list_managed_users"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/managed-users/{id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Detail */
        get: operations["admin_managed_user"];
        put?: never;
        post?: never;
        /** Remove */
        delete: operations["admin_delete_managed_user"];
        options?: never;
        head?: never;
        /** Save */
        patch: operations["admin_update_managed_user"];
        trace?: never;
    };
    "/api/v1/admin/managed-users/{id}/credit-adjustments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Adjustment */
        post: operations["admin_adjust_managed_credits"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/managed-users/{id}/password-reset": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Reset */
        post: operations["admin_reset_managed_password"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/media-agents/image/models": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Image Models */
        get: operations["admin_image_models"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update Image Models */
        patch: operations["admin_save_image_models"];
        trace?: never;
    };
    "/api/v1/admin/media-agents/video/audio": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Video Audio */
        get: operations["admin_video_audio"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update Video Audio */
        patch: operations["admin_save_video_audio"];
        trace?: never;
    };
    "/api/v1/admin/media-agents/video/models": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Video Models */
        get: operations["admin_video_models"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/media-agents/video/models/{role}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update Video Model */
        patch: operations["admin_save_video_model"];
        trace?: never;
    };
    "/api/v1/admin/media-agents/{kind}/connection": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Connection */
        get: operations["admin_media_connection"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Save Connection */
        patch: operations["admin_save_media_connection"];
        trace?: never;
    };
    "/api/v1/admin/media-agents/{kind}/resources/{resource}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Resources */
        get: operations["admin_media_resources"];
        put?: never;
        /** Create Resource */
        post: operations["admin_create_media_resource"];
        delete?: never;
        options?: never;
        head?: never;
        /** Update Singleton */
        patch: operations["admin_update_media_singleton"];
        trace?: never;
    };
    "/api/v1/admin/media-agents/{kind}/resources/{resource}/{config_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Resource */
        get: operations["admin_media_resource"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update Resource */
        patch: operations["admin_update_media_resource"];
        trace?: never;
    };
    "/api/v1/admin/parameter-config": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Parameter Config */
        get: operations["admin_get_parameter_config"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Save Parameter Config */
        patch: operations["admin_update_parameter_config"];
        trace?: never;
    };
    "/api/v1/admin/registration-credit-config": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Registration Config */
        get: operations["admin_get_registration_credit_config"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update Registration Config */
        patch: operations["admin_update_registration_credit_config"];
        trace?: never;
    };
    "/api/v1/admin/site/cases": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Admin Cases */
        get: operations["admin_site_cases"];
        put?: never;
        /** Publish Case */
        post: operations["publish_site_case"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/site/cases/{case_id}/withdraw": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Withdraw Case */
        post: operations["withdraw_site_case"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/site/content": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Admin Content */
        get: operations["admin_site_content"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update Content */
        patch: operations["update_site_content"];
        trace?: never;
    };
    "/api/v1/admin/statistics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Statistics */
        get: operations["admin_statistics"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/tasks": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Tasks */
        get: operations["admin_list_tasks"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/tasks/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Summary Tasks */
        get: operations["admin_tasks_summary"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/tasks/{id}/diagnostics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Task Diagnostics */
        get: operations["admin_task_diagnostics"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/tasks/{id}/investigations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Open Investigation */
        post: operations["open_investigation"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/tasks/{id}/resolutions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Resolve Investigation */
        post: operations["resolve_investigation"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/text-default-model": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Default Model */
        get: operations["admin_text_default_model"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Save Default Model */
        patch: operations["admin_save_text_default_model"];
        trace?: never;
    };
    "/api/v1/admin/text-model-configs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Models */
        get: operations["admin_text_models"];
        put?: never;
        /** Create Model */
        post: operations["admin_create_text_model"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/text-model-configs/{config_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Model */
        get: operations["admin_text_model"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update Model */
        patch: operations["admin_update_text_model"];
        trace?: never;
    };
    "/api/v1/admin/text-service-connection": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Connection */
        get: operations["admin_text_service_connection"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Save Connection */
        patch: operations["admin_save_text_service_connection"];
        trace?: never;
    };
    "/api/v1/admin/users": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Users */
        get: operations["admin_list_users"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/users/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Summary Users */
        get: operations["admin_users_summary"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/users/{id}/account": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Account */
        get: operations["admin_user_account"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/users/{id}/ledger": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Ledger */
        get: operations["admin_user_ledger"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/users/{id}/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Set Account Status */
        patch: operations["set_account_status"];
        trace?: never;
    };
    "/api/v1/agent-callbacks/{agent_id}/{version}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Receive Callback */
        post: operations["receive_agent_callback"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/agents": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Agents */
        get: operations["list_agents"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/assist/prompts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Prepare Prompt
         * @description Prepare a draft; request_key is the required Idempotency-Key header, not a body field.
         */
        post: operations["prepare_prompt"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/login": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Login */
        post: operations["auth_login"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Logout */
        post: operations["auth_logout"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/password": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Change Password */
        post: operations["auth_change_password"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/register": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Register */
        post: operations["auth_register"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/conversations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Conversations */
        get: operations["list_conversations"];
        put?: never;
        /** Create Conversation */
        post: operations["create_conversation"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/conversations/{id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Conversation */
        get: operations["get_conversation"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Events
         * @description Same-origin Secure HttpOnly cookie EventSource. Origin may be absent when Sec-Fetch-Site is same-origin; no custom CSRF or X-Requested-With header. Cursor is the opaque SSE id (user UUID:sequence); Last-Event-ID takes precedence over after. Invalid, foreign, ahead or expired cursors receive a generic reset with this user's current cursor and the stream closes. GET original persisted resources after reset; never POST a replacement task. Default transport retention is 7 days; permanent sequence and deduplication receipts are retained. Unstored fragments have no id and cannot be replayed. Real upstream streaming is disabled pending D-01. Redis is unnecessary for correctness.
         */
        get: operations["events_stream"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/files": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Upload */
        post: operations["upload_file"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/files/{file_id}/content": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Content */
        get: operations["read_file_content"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/files/{id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Material */
        delete: operations["delete_material"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/health/live": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Live */
        get: operations["health_live"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/health/ready": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Ready */
        get: operations["health_ready"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Profile */
        get: operations["get_profile"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update Profile */
        patch: operations["update_profile"];
        trace?: never;
    };
    "/api/v1/products/versions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Product Version */
        post: operations["create_product_version"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/products/versions/{version}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Product Version */
        get: operations["get_product_version"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/quick-generation": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Runs */
        get: operations["list_quick_generation"];
        put?: never;
        /** Create */
        post: operations["create_quick_generation"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/quick-generation/{id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read */
        get: operations["get_quick_generation"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Save */
        patch: operations["save_quick_generation"];
        trace?: never;
    };
    "/api/v1/quick-generation/{id}/advance": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Advance */
        post: operations["advance_quick_generation"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/quick-generation/{id}/batches/{batch_id}/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Cancel Batch */
        post: operations["cancel_quick_generation_batch"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/quick-generation/{id}/batches/{batch_id}/submit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Submit */
        post: operations["submit_quick_generation"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/quick-generation/{id}/prepare": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Prepare */
        post: operations["prepare_quick_generation"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/quotes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Quote */
        post: operations["quote_generation"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/site/cases": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Cases */
        get: operations["public_site_cases"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/site/cases/{case_id}/copies/{copy_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Case Copy */
        get: operations["public_site_copy"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/site/content": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Content */
        get: operations["public_site_content"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Tasks */
        get: operations["list_tasks"];
        put?: never;
        /** Admit Task */
        post: operations["admit_task"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Task */
        get: operations["get_task"];
        put?: never;
        post?: never;
        /** Delete Task History */
        delete: operations["delete_task_history"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{id}/history": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Task History */
        get: operations["task_history"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{id}/regeneration-quote": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Quote Task Regeneration */
        post: operations["quote_task_regeneration"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{id}/release": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Release Failed Task */
        post: operations["release_failed_task"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{id}/retry": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Retry Failed Task */
        post: operations["retry_failed_task"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{id}/video/confirm": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Confirm Video Plan */
        post: operations["confirm_video_plan"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{id}/video/inputs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Supplement Video Inputs */
        post: operations["supplement_video_inputs"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{id}/video/plan-revisions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Revise Video Plan */
        post: operations["revise_video_plan"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{task_id}/investigation": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Own Investigation */
        get: operations["get_own_investigation"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/video-options": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Video Options */
        get: operations["video_options"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/works": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Works */
        get: operations["list_works"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/works/{id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Work */
        get: operations["get_work"];
        put?: never;
        post?: never;
        /** Delete Work */
        delete: operations["delete_work"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AccountLedgerPage */
        AccountLedgerPage: {
            consumption: components["schemas"]["LedgerConsumption"];
            /** Items */
            items: components["schemas"]["LedgerEntryView"][];
            /** Next Cursor */
            next_cursor: string | null;
            /** Page */
            page?: number | null;
            /** Page Size */
            page_size: number;
            /** Total */
            total: number;
        };
        /** AccountStatusReceipt */
        AccountStatusReceipt: {
            /** Auth Version */
            auth_version: number;
            /** Policy Version */
            policy_version: string;
            /**
             * Status
             * @enum {string}
             */
            status: "active" | "disabled";
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
        };
        /** AccountStatusRequest */
        AccountStatusRequest: {
            /** Expected Auth Version */
            expected_auth_version: number;
            /** Policy Version */
            policy_version: string;
            /**
             * Status
             * @enum {string}
             */
            status: "active" | "disabled";
        };
        /** AccountView */
        AccountView: {
            /** Available */
            available: number;
            /** Consumed */
            consumed: number;
            /** Credited Total */
            credited_total: number;
            /** Frozen */
            frozen: number;
        };
        /** AdminAuditSummary */
        AdminAuditSummary: {
            /** Action Counts */
            action_counts: {
                [key: string]: number;
            };
            /** Total */
            total: number;
        };
        /** AdminCaseView */
        AdminCaseView: {
            /** Authorization Ref */
            authorization_ref: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Owner Id
             * Format: uuid
             */
            owner_id: string;
            /** Policy Version */
            policy_version: string;
            /**
             * State
             * @enum {string}
             */
            state: "published" | "cleanup_pending" | "withdrawn";
            /** Withdrawal Policy Version */
            withdrawal_policy_version: string | null;
            /**
             * Work Id
             * Format: uuid
             */
            work_id: string;
        };
        /** AdminLedgerEntryView */
        AdminLedgerEntryView: {
            /** Account */
            account: string;
            /** Amount */
            amount: number;
            balances_after: components["schemas"]["LedgerBalances"];
            balances_before: components["schemas"]["LedgerBalances"];
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Grant Id */
            grant_id: string | null;
            /** Kind */
            kind: string;
            /**
             * Ledger Id
             * Format: uuid
             */
            ledger_id: string;
            /** Operator */
            operator?: string | null;
            /** Reason */
            reason: string;
            /** Reservation Id */
            reservation_id: string | null;
            /** Task Id */
            task_id: string | null;
            /** Task Name */
            task_name?: string | null;
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
        };
        /** AdminLedgerSummary */
        AdminLedgerSummary: {
            /** Available */
            available: number;
            /** Consumed */
            consumed: number;
            /** Credited Total */
            credited_total: number;
            /** Frozen */
            frozen: number;
            /** Ledger Count */
            ledger_count: number;
        };
        /** AdminTasksSummary */
        AdminTasksSummary: {
            /** Frozen Credits */
            frozen_credits: number;
            /** Investigating */
            investigating: number;
            /** Save Recovery */
            save_recovery: number;
            /** Total */
            total: number;
        };
        /** AdminUserView */
        AdminUserView: {
            /** Account Normalized */
            account_normalized: string;
            /** Auth Version */
            auth_version: number;
            /**
             * Available
             * @default 0
             */
            available: number;
            /** Category */
            category?: string | null;
            /**
             * Consumed
             * @default 0
             */
            consumed: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Email */
            email?: string | null;
            /**
             * Frozen
             * @default 0
             */
            frozen: number;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Last Login At */
            last_login_at?: string | null;
            /** Nickname */
            nickname: string | null;
            /** Phone */
            phone?: string | null;
            /**
             * Role
             * @enum {string}
             */
            role: "user" | "admin";
            /** Shop Name */
            shop_name?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "active" | "disabled";
            /**
             * Task Count
             * @default 0
             */
            task_count: number;
        };
        /** AdminUsersSummary */
        AdminUsersSummary: {
            /** Active */
            active: number;
            /** Admin Count */
            admin_count: number;
            /** Available */
            available: number;
            /** Consumed */
            consumed: number;
            /** Credited Total */
            credited_total: number;
            /** Disabled */
            disabled: number;
            /** Frozen */
            frozen: number;
            /** Total */
            total: number;
        };
        /** AdmissionResult */
        AdmissionResult: {
            /** Replayed */
            replayed: boolean;
            task: components["schemas"]["TaskView"];
        };
        /** AgentDescriptions */
        AgentDescriptions: {
            /** Image */
            image: string;
            /** Text */
            text: string;
            /** Video */
            video: string;
        };
        /** AgentDraft */
        AgentDraft: {
            /**
             * Agent Id
             * Format: uuid
             */
            agent_id: string;
            /** Enabled */
            enabled: boolean;
            /**
             * Endpoint
             * Format: password
             */
            endpoint: string;
            /** Expected Version */
            expected_version?: string | null;
            input_support: components["schemas"]["InputSupport"];
            /**
             * Kind
             * @enum {string}
             */
            kind: "copy" | "image" | "video";
            /**
             * Mode
             * @enum {string}
             */
            mode: "mock" | "staging" | "production";
            /** Name */
            name: string;
            /** Policy Versions */
            policy_versions: {
                [key: string]: string;
            };
            /** Protocol Version */
            protocol_version: string;
            /** Secret Ref */
            secret_ref?: string | null;
            /** Test Only */
            test_only: boolean;
            /** Version */
            version: string;
        };
        /** AgentUsageView */
        AgentUsageView: {
            /**
             * Agent Id
             * Format: uuid
             */
            agent_id: string;
            /** Credits Consumed */
            credits_consumed: number;
            /** Credits Frozen */
            credits_frozen: number;
            /** Credits Released */
            credits_released: number;
            /** Failed Count */
            failed_count: number;
            /** Manually Closed Count */
            manually_closed_count: number;
            /** Succeeded Count */
            succeeded_count: number;
            /** Success Rate */
            success_rate: number | null;
            /** Task Count */
            task_count: number;
            /** Terminal Count */
            terminal_count: number;
            /** Unsettled Count */
            unsettled_count: number;
        };
        /** AgentVersion */
        AgentVersion: {
            /**
             * Agent Id
             * Format: uuid
             */
            agent_id: string;
            /** Enabled */
            enabled: boolean;
            input_support: components["schemas"]["InputSupport"];
            /**
             * Kind
             * @enum {string}
             */
            kind: "copy" | "image" | "video";
            /**
             * Mode
             * @enum {string}
             */
            mode: "mock" | "staging" | "production";
            /** Name */
            name: string;
            /** Policy Versions */
            policy_versions: {
                [key: string]: string;
            };
            /** Protocol Version */
            protocol_version: string;
            /** Secret Configured */
            secret_configured: boolean;
            /** Test Only */
            test_only: boolean;
            /** Version */
            version: string;
        };
        /** AlertView */
        AlertView: {
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Disposition */
            disposition: string;
            /** Escalation Ref */
            escalation_ref: string;
            /** Evidence Ref */
            evidence_ref: string | null;
            /** Key */
            key: string;
            /** Kind */
            kind: string;
            /**
             * Task Id
             * Format: uuid
             */
            task_id: string;
        };
        /** AssignInvestigation */
        AssignInvestigation: {
            /** Evidence */
            evidence: string;
            /** Expected Version */
            expected_version: number;
            /**
             * Owner
             * Format: uuid
             */
            owner: string;
            /** Policy Version */
            policy_version: string;
            /** Reason */
            reason: string;
        };
        /** AssistProposal */
        AssistProposal: {
            /** Agent Version */
            agent_version: string;
            /** Missing Facts */
            missing_facts: string[];
            /** Original */
            original: string;
            /** Parameters */
            parameters: {
                [key: string]: string | number | boolean;
            };
            /** Policy Version */
            policy_version: string;
            /** Proposed */
            proposed: string;
            /** Spec Version */
            spec_version: string;
            /**
             * Test Only
             * @default true
             */
            test_only: boolean;
        };
        /** AssistRequest */
        AssistRequest: {
            /**
             * Agent Id
             * Format: uuid
             */
            agent_id: string;
            /** Agent Version */
            agent_version: string;
            /** Material Versions */
            material_versions: components["schemas"]["FileVersionRef"][];
            /** Original */
            original: string;
            /** Parameters */
            parameters: {
                [key: string]: string | number | boolean;
            };
            /** Product */
            product: {
                [key: string]: unknown;
            };
        };
        /** AuditView */
        AuditView: {
            /** Action */
            action: string;
            /** Actor Id */
            actor_id: string | null;
            /** Changes */
            changes: {
                [key: string]: unknown;
            };
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Object Id */
            object_id: string;
            /** Reason */
            reason: string;
        };
        /** AuditedContent */
        AuditedContent: {
            /**
             * Audit Id
             * Format: uuid
             */
            audit_id: string;
            /** Content */
            content: {
                [key: string]: unknown;
            };
            /**
             * Grant Id
             * Format: uuid
             */
            grant_id: string;
            /**
             * Resource Id
             * Format: uuid
             */
            resource_id: string;
            /**
             * Resource Type
             * @enum {string}
             */
            resource_type: "message" | "work" | "file" | "material" | "conversation" | "task" | "product_version";
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
        };
        /** AuthView */
        AuthView: {
            profile: components["schemas"]["ProfileView"];
            /** Replayed */
            replayed: boolean;
        };
        /** CasePublish */
        CasePublish: {
            /** Authorization Ref */
            authorization_ref: string;
            /** Policy Version */
            policy_version: string;
            /** Policy Versions */
            policy_versions: {
                [key: string]: string;
            };
            /**
             * Work Id
             * Format: uuid
             */
            work_id: string;
        };
        /** CaseWithdraw */
        CaseWithdraw: {
            /** Policy Version */
            policy_version: string;
        };
        /** ContentGrantRequest */
        ContentGrantRequest: {
            /**
             * Actor Id
             * Format: uuid
             */
            actor_id: string;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
            /** Reason */
            reason: string;
            scope: components["schemas"]["ContentScope"];
        };
        /** ContentGrantView */
        ContentGrantView: {
            /**
             * Actor Id
             * Format: uuid
             */
            actor_id: string;
            /**
             * Approver Id
             * Format: uuid
             */
            approver_id: string;
            /** Authority Source */
            authority_source: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Mode
             * @enum {string}
             */
            mode: "mock" | "staging" | "production";
            /** Reason */
            reason: string;
            /**
             * Resource Id
             * Format: uuid
             */
            resource_id: string;
            /**
             * Resource Type
             * @enum {string}
             */
            resource_type: "message" | "work" | "file" | "material" | "conversation" | "task" | "product_version";
            /** Revoke Reason */
            revoke_reason: string | null;
            /** Revoked At */
            revoked_at: string | null;
            /** Revoked By */
            revoked_by: string | null;
            /** Test Only */
            test_only: boolean;
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
        };
        /** ContentScope */
        ContentScope: {
            /**
             * Resource Id
             * Format: uuid
             */
            resource_id: string;
            /**
             * Resource Type
             * @enum {string}
             */
            resource_type: "message" | "work" | "file" | "material" | "conversation" | "task" | "product_version";
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
        };
        /** ConversationCreate */
        ConversationCreate: {
            /** Title */
            title: string;
        };
        /** ConversationSummary */
        ConversationSummary: {
            /**
             * Conversation Id
             * Format: uuid
             */
            conversation_id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Display Number */
            readonly display_number: string;
            /** Title */
            title: string;
        };
        /** ConversationView */
        ConversationView: {
            conversation: components["schemas"]["ConversationSummary"];
            messages: components["schemas"]["CursorPage_MessageView_"];
            tasks: components["schemas"]["CursorPage_TaskView_"];
        };
        /** CreditAdjustment */
        CreditAdjustment: {
            /**
             * Business Key
             * Format: uuid
             */
            business_key: string;
            /** Delta */
            delta: number;
            /** Reason */
            reason: string;
        };
        /** CreditAdjustmentReceipt */
        CreditAdjustmentReceipt: {
            /**
             * Actor Id
             * Format: uuid
             */
            actor_id: string;
            /**
             * Business Key
             * Format: uuid
             */
            business_key: string;
            /** Delta */
            delta: number;
            /**
             * Ledger Id
             * Format: uuid
             */
            ledger_id: string;
            /** Reason */
            reason: string;
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
        };
        /** CreditGrantRequest */
        CreditGrantRequest: {
            /** Amount */
            amount: number;
            /** Business Key */
            business_key: string;
            /** Reason */
            reason: string;
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
        };
        /** CreditGrantView */
        CreditGrantView: {
            /**
             * Actor Id
             * Format: uuid
             */
            actor_id: string;
            /** Amount */
            amount: number;
            /** Business Key */
            business_key: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Reason */
            reason: string;
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
        };
        /** CursorPage[AdminUserView] */
        CursorPage_AdminUserView_: {
            /** Items */
            items: components["schemas"]["AdminUserView"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** CursorPage[AlertView] */
        CursorPage_AlertView_: {
            /** Items */
            items: components["schemas"]["AlertView"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** CursorPage[ContentGrantView] */
        CursorPage_ContentGrantView_: {
            /** Items */
            items: components["schemas"]["ContentGrantView"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** CursorPage[ConversationSummary] */
        CursorPage_ConversationSummary_: {
            /** Items */
            items: components["schemas"]["ConversationSummary"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** CursorPage[InvestigationView] */
        CursorPage_InvestigationView_: {
            /** Items */
            items: components["schemas"]["InvestigationView"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** CursorPage[MessageView] */
        CursorPage_MessageView_: {
            /** Items */
            items: components["schemas"]["MessageView"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** CursorPage[TaskView] */
        CursorPage_TaskView_: {
            /** Items */
            items: components["schemas"]["TaskView"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** DailyUsageView */
        DailyUsageView: {
            /**
             * Active User Count
             * @default 0
             */
            active_user_count: number;
            /** Credits Consumed */
            credits_consumed: number;
            /**
             * Date
             * Format: date
             */
            date: string;
            /**
             * Registered Count
             * @default 0
             */
            registered_count: number;
            /** Task Count */
            task_count: number;
        };
        /** DeleteReceipt */
        DeleteReceipt: {
            /**
             * Deleted
             * @constant
             */
            deleted: true;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Policy Version */
            policy_version: string;
        };
        /** DeleteRequest */
        DeleteRequest: {
            /** Policy Version */
            policy_version: string;
        };
        /** DurableEventView */
        DurableEventView: {
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Event Seq */
            event_seq: number;
            payload: components["schemas"]["TaskEventPayload"];
        };
        /**
         * ErrorCode
         * @enum {string}
         */
        ErrorCode: "COMMAND_REJECTED" | "MATERIAL_UNAVAILABLE" | "INPUT_INVALID" | "SPEC_DISABLED" | "QUOTE_STALE" | "IDEMPOTENCY_CONFLICT" | "INSUFFICIENT_CREDITS" | "ADJUSTMENT_TARGET_DELETED" | "CAPACITY_INSUFFICIENT" | "FEATURE_NOT_ENABLED" | "RATE_LIMITED" | "UNAUTHENTICATED" | "FORBIDDEN" | "NOT_FOUND" | "METHOD_NOT_ALLOWED" | "INTERNAL_ERROR";
        /** ErrorDetail */
        ErrorDetail: {
            code: components["schemas"]["ErrorCode"];
            /**
             * Current Quotes
             * @default null
             */
            current_quotes: components["schemas"]["Quote"][] | null;
            /**
             * Current Specs
             * @default null
             */
            current_specs: components["schemas"]["SpecVersion"][] | null;
            /** Message */
            message: string;
        };
        /** ErrorResponse */
        ErrorResponse: {
            error: components["schemas"]["ErrorDetail"];
            /**
             * Trace Id
             * Format: uuid
             */
            trace_id: string;
        };
        /** EventReceipt */
        EventReceipt: {
            /** Reference */
            reference?: string | null;
            /** Status */
            status: string;
        };
        /** Evidence */
        Evidence: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "review" | "upstream_failure" | "durable_delivery";
            /** Reference */
            reference: string;
        };
        /** FileVersionRef */
        FileVersionRef: {
            /**
             * File Id
             * Format: uuid
             */
            file_id: string;
            /** Version */
            version: string;
        };
        /** ImageModelSetting */
        ImageModelSetting: {
            /** Api Key */
            api_key?: string | null;
            /** Base Url */
            base_url: string;
            /** Model */
            model: string;
            /**
             * Protocol
             * @enum {string}
             */
            protocol: "openrouter_images" | "openai_images" | "chat_completions";
        };
        /** ImageModelSettingView */
        ImageModelSettingView: {
            /** Base Url */
            base_url: string;
            /** Enabled */
            enabled: boolean;
            /** Has Api Key */
            has_api_key: boolean;
            /** Model */
            model: string;
            /**
             * Protocol
             * @enum {string}
             */
            protocol: "openrouter_images" | "openai_images" | "chat_completions";
        };
        /** ImageModelsUpdate */
        ImageModelsUpdate: {
            /** Expected Revision */
            expected_revision: number;
            /** Expected Versions */
            expected_versions: {
                [key: string]: number;
            };
            image_model: components["schemas"]["ImageModelSetting"];
            text_model: components["schemas"]["ImageModelSetting"];
        };
        /** ImageModelsView */
        ImageModelsView: {
            image_model: components["schemas"]["ImageModelSettingView"] | null;
            /** Revision */
            revision: number;
            text_model: components["schemas"]["ImageModelSettingView"] | null;
            /** Versions */
            versions: {
                [key: string]: number;
            };
        };
        /** InputSnapshot */
        InputSnapshot: {
            /** Instruction */
            instruction: string;
            /** Material Versions */
            material_versions: components["schemas"]["FileVersionRef"][];
            /** Parameters */
            parameters: {
                [key: string]: unknown;
            };
            /** Product */
            product: {
                [key: string]: unknown;
            };
            /** Product Version */
            product_version: string;
        };
        /** InputSupport */
        InputSupport: {
            /** Instruction Required */
            instruction_required: boolean;
            /** Max Materials */
            max_materials: number;
            /** Min Materials */
            min_materials: number;
            /** Product Required Fields */
            product_required_fields: string[];
        };
        /** InvestigationView */
        InvestigationView: {
            /**
             * Deadline At
             * Format: date-time
             */
            deadline_at: string;
            /** Owner */
            owner: string | null;
            /** Policy Version */
            policy_version: string;
            /** Status */
            status: string;
            /**
             * Task Id
             * Format: uuid
             */
            task_id: string;
            /** User Reason */
            user_reason: string | null;
            /** Version */
            version: number;
        };
        JsonValue: unknown;
        /** LedgerBalances */
        LedgerBalances: {
            /** Available */
            available: number;
            /** Consumed */
            consumed: number;
            /** Frozen */
            frozen: number;
        };
        /** LedgerConsumption */
        LedgerConsumption: {
            /**
             * Copy
             * @default 0
             */
            copy: number;
            /**
             * Image
             * @default 0
             */
            image: number;
            /**
             * Other
             * @default 0
             */
            other: number;
            /**
             * Video
             * @default 0
             */
            video: number;
        };
        /** LedgerEntryView */
        LedgerEntryView: {
            /** Amount */
            amount: number;
            balances_after: components["schemas"]["LedgerBalances"];
            balances_before: components["schemas"]["LedgerBalances"];
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Grant Id */
            grant_id: string | null;
            /** Kind */
            kind: string;
            /**
             * Ledger Id
             * Format: uuid
             */
            ledger_id: string;
            /** Reason */
            reason: string;
            /** Reservation Id */
            reservation_id: string | null;
            /** Task Id */
            task_id: string | null;
            /** Task Name */
            task_name?: string | null;
        };
        /** LiveResponse */
        LiveResponse: {
            /** Live */
            live: boolean;
            /**
             * Mode
             * @enum {string}
             */
            mode: "mock" | "staging" | "production";
            /** Test Only */
            test_only: boolean;
        };
        /** LoginRequest */
        LoginRequest: {
            /** Account */
            account: string;
            /**
             * Password
             * Format: password
             */
            password: string;
        };
        /** ManagedPasswordReset */
        ManagedPasswordReset: {
            /** Expected Auth Version */
            expected_auth_version: number;
            /**
             * New Password
             * Format: password
             */
            new_password: string;
            /** Reason */
            reason: string;
        };
        /** ManagedUserDelete */
        ManagedUserDelete: {
            /** Expected Auth Version */
            expected_auth_version: number;
            /** Reason */
            reason: string;
        };
        /** ManagedUserUpdate */
        ManagedUserUpdate: {
            /** Account */
            account: string;
            avatar?: components["schemas"]["FileVersionRef"] | null;
            /** Bio */
            bio?: string | null;
            /** Category */
            category?: string | null;
            /** Email */
            email?: string | null;
            /** Expected Auth Version */
            expected_auth_version: number;
            /** Expected Profile Version */
            expected_profile_version: string;
            /** Nickname */
            nickname?: string | null;
            /** Phone */
            phone?: string | null;
            /** Reason */
            reason: string;
            /**
             * Role
             * @enum {string}
             */
            role: "user" | "admin";
            /** Shop Name */
            shop_name?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "active" | "disabled";
        };
        /** ManagedUserView */
        ManagedUserView: {
            /** Account Normalized */
            account_normalized: string;
            /** Auth Version */
            auth_version: number;
            /**
             * Available
             * @default 0
             */
            available: number;
            /** Category */
            category?: string | null;
            /**
             * Consumed
             * @default 0
             */
            consumed: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Email */
            email?: string | null;
            /**
             * Frozen
             * @default 0
             */
            frozen: number;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Last Login At */
            last_login_at?: string | null;
            /** Nickname */
            nickname: string | null;
            /** Phone */
            phone?: string | null;
            /** Profile Version */
            profile_version: string;
            /**
             * Role
             * @enum {string}
             */
            role: "user" | "admin";
            /** Shop Name */
            shop_name?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "active" | "disabled";
            /**
             * Task Count
             * @default 0
             */
            task_count: number;
        };
        /** MediaConnectionUpdate */
        MediaConnectionUpdate: {
            /** Base Url */
            base_url?: string | null;
            /** Default Config Id */
            default_config_id?: string | null;
            /** Expected Revision */
            expected_revision: number;
            /** Image Model */
            image_model?: ("pro" | "fast" | "base") | null;
            /** Management Key */
            management_key?: string | null;
            /** Service Key */
            service_key?: string | null;
            /** Video Audio Enabled */
            video_audio_enabled?: boolean | null;
        };
        /** MediaConnectionView */
        MediaConnectionView: {
            /** Base Url */
            base_url: string | null;
            /** Default Config Id */
            default_config_id: string | null;
            /** Has Management Key */
            has_management_key: boolean;
            /** Has Service Key */
            has_service_key: boolean;
            /** Id */
            id: string | null;
            /** Image Model */
            image_model: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "image" | "video";
            /** Revision */
            revision: number;
        };
        /** MediaResourceWrite */
        MediaResourceWrite: {
            /** Config */
            config: {
                [key: string]: components["schemas"]["JsonValue"];
            };
            /** Expected Connection Revision */
            expected_connection_revision?: number | null;
        };
        /** MessageView */
        MessageView: {
            /** Content */
            content: {
                [key: string]: unknown;
            };
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "authored" | "final";
            /**
             * Message Id
             * Format: uuid
             */
            message_id: string;
            /**
             * Role
             * @enum {string}
             */
            role: "user" | "assistant";
            /** Task Id */
            task_id: string | null;
        };
        /** NumberedPage[AdminLedgerEntryView] */
        NumberedPage_AdminLedgerEntryView_: {
            /** Items */
            items: components["schemas"]["AdminLedgerEntryView"][];
            /** Next Cursor */
            next_cursor: string | null;
            /** Page */
            page?: number | null;
            /** Page Size */
            page_size: number;
            /** Total */
            total: number;
        };
        /** NumberedPage[AuditView] */
        NumberedPage_AuditView_: {
            /** Items */
            items: components["schemas"]["AuditView"][];
            /** Next Cursor */
            next_cursor: string | null;
            /** Page */
            page?: number | null;
            /** Page Size */
            page_size: number;
            /** Total */
            total: number;
        };
        /** NumberedPage[LedgerEntryView] */
        NumberedPage_LedgerEntryView_: {
            /** Items */
            items: components["schemas"]["LedgerEntryView"][];
            /** Next Cursor */
            next_cursor: string | null;
            /** Page */
            page?: number | null;
            /** Page Size */
            page_size: number;
            /** Total */
            total: number;
        };
        /** NumberedPage[ManagedUserView] */
        NumberedPage_ManagedUserView_: {
            /** Items */
            items: components["schemas"]["ManagedUserView"][];
            /** Next Cursor */
            next_cursor: string | null;
            /** Page */
            page?: number | null;
            /** Page Size */
            page_size: number;
            /** Total */
            total: number;
        };
        /** NumberedPage[TaskDiagnosticView] */
        NumberedPage_TaskDiagnosticView_: {
            /** Items */
            items: components["schemas"]["TaskDiagnosticView"][];
            /** Next Cursor */
            next_cursor: string | null;
            /** Page */
            page?: number | null;
            /** Page Size */
            page_size: number;
            /** Total */
            total: number;
        };
        /** OpenInvestigation */
        OpenInvestigation: {
            /** Evidence */
            evidence: string;
            /**
             * Owner
             * Format: uuid
             */
            owner: string;
            /** Policy Version */
            policy_version: string;
        };
        /** OwnerView */
        OwnerView: {
            /**
             * Deadline At
             * Format: date-time
             */
            deadline_at: string;
            /** Status */
            status: string;
            /**
             * Task Id
             * Format: uuid
             */
            task_id: string;
            /** User Reason */
            user_reason: string | null;
        };
        /** PageQuery */
        PageQuery: {
            /**
             * Cursor
             * @default null
             */
            cursor: string | null;
            /**
             * Limit
             * @default 20
             */
            limit: number;
        };
        /** ParameterConfigUpdate */
        ParameterConfigUpdate: {
            /** Assist Api Key */
            assist_api_key?: string | null;
            /** Assist Base Url */
            assist_base_url?: string | null;
            /** Assist Model */
            assist_model?: string | null;
            /** Expected Version */
            expected_version: string | null;
            /** Image Price */
            image_price: number | null;
            /** Text Price */
            text_price: number | null;
            /** Video Price */
            video_price: number | null;
        };
        /** ParameterConfigView */
        ParameterConfigView: {
            /** Assist Base Url */
            assist_base_url?: string | null;
            /** Assist Model */
            assist_model?: string | null;
            /**
             * Has Assist Api Key
             * @default false
             */
            has_assist_api_key: boolean;
            /** Image Price */
            image_price: number | null;
            /** Text Price */
            text_price: number | null;
            /** Version */
            version: string | null;
            /** Video Price */
            video_price: number | null;
        };
        /** ParameterRule */
        ParameterRule: {
            /**
             * Choices
             * @default null
             */
            choices: (string | number | boolean)[] | null;
            /**
             * Default
             * @default null
             */
            default: string | number | boolean | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "string" | "integer" | "boolean";
            /**
             * Max Length
             * @default null
             */
            max_length: number | null;
            /**
             * Maximum
             * @default null
             */
            maximum: number | null;
            /**
             * Minimum
             * @default null
             */
            minimum: number | null;
            /** Required */
            required: boolean;
        };
        /** ParameterSchema */
        ParameterSchema: {
            /** Combinations */
            combinations: {
                [key: string]: string | number | boolean;
            }[];
            /** Fields */
            fields: {
                [key: string]: components["schemas"]["ParameterRule"];
            };
        };
        /** PasswordChangeRequest */
        PasswordChangeRequest: {
            /**
             * Current Password
             * Format: password
             */
            current_password: string;
            /**
             * New Password
             * Format: password
             */
            new_password: string;
        };
        /** Principal */
        Principal: {
            /** Auth Version */
            auth_version: number;
            role: components["schemas"]["UserRole"];
            /**
             * Session Id
             * Format: uuid
             */
            session_id: string;
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
        };
        /** ProductVersionCreate */
        ProductVersionCreate: {
            /** Product */
            product: {
                /** @enum {string} */
                product_type?: "clothing" | "shoes_bags" | "beauty" | "food" | "digital" | "home" | "appliances" | "sports" | "baby" | "other";
            } & {
                [key: string]: unknown;
            };
            /** Product Id */
            product_id?: string | null;
        };
        /** ProductVersionView */
        ProductVersionView: {
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Product */
            product: {
                [key: string]: unknown;
            };
            /**
             * Product Id
             * Format: uuid
             */
            product_id: string;
            /**
             * Version
             * Format: uuid
             */
            version: string;
        };
        /** ProfileUpdate */
        ProfileUpdate: {
            avatar?: components["schemas"]["FileVersionRef"] | null;
            /** Bio */
            bio?: string | null;
            /** Category */
            category?: string | null;
            /** Email */
            email?: string | null;
            /** Nickname */
            nickname?: string | null;
            /** Phone */
            phone?: string | null;
            /** Shop Name */
            shop_name?: string | null;
        };
        /** ProfileView */
        ProfileView: {
            /** Account */
            account: string;
            avatar: components["schemas"]["FileVersionRef"] | null;
            /** Bio */
            bio: string | null;
            /** Category */
            category: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Email */
            email: string | null;
            /** Last Login At */
            last_login_at: string | null;
            /** Nickname */
            nickname: string | null;
            /** Phone */
            phone: string | null;
            role: components["schemas"]["UserRole"];
            /** Shop Name */
            shop_name: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "active" | "disabled";
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
        };
        /** PublicCaseView */
        PublicCaseView: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Items */
            items: components["schemas"]["PublicCopyView"][];
        };
        /** PublicCopyView */
        PublicCopyView: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Media Type */
            media_type: string;
            /** Url */
            url: string;
        };
        /** PublicSiteView */
        PublicSiteView: {
            content: components["schemas"]["SiteContentView"] | null;
        };
        /** QuickAdvance */
        QuickAdvance: {
            /**
             * Action
             * @enum {string}
             */
            action: "confirm_copy" | "confirm_images" | "finish" | "back";
            /** Version */
            version: number;
        };
        /** QuickBatch */
        QuickBatch: {
            /** Draft Digest */
            draft_digest: string;
            /** Id */
            id: string;
            /** Items */
            items: components["schemas"]["QuickBatchItem"][];
            /**
             * Kind
             * @enum {string}
             */
            kind: "copy" | "image" | "video";
            /**
             * Submitted
             * @default false
             */
            submitted: boolean;
        };
        /** QuickBatchItem */
        QuickBatchItem: {
            /**
             * Free Regeneration
             * @default false
             */
            free_regeneration: boolean;
            /**
             * Free Regenerations Used
             * @default 0
             */
            free_regenerations_used: number;
            /** Label */
            label: string;
            /** Regeneration Of */
            regeneration_of?: string | null;
            request: components["schemas"]["SubmitTaskRequest"];
            /** Task Id */
            task_id?: string | null;
        };
        /** QuickCreate */
        QuickCreate: {
            /**
             * Run Id
             * Format: uuid
             */
            run_id: string;
        };
        /** QuickDraft */
        QuickDraft: {
            /**
             * Copy Instruction
             * @default
             */
            copy_instruction: string;
            /** Copy Parameters */
            copy_parameters?: {
                [key: string]: string | number | boolean;
            };
            /**
             * Copy Text
             * @default
             */
            copy_text: string;
            /** Copy Texts */
            copy_texts?: {
                [key: string]: string;
            };
            /** Copy Types */
            copy_types?: string[];
            /**
             * Image Instruction
             * @default
             */
            image_instruction: string;
            /** Image Outputs */
            image_outputs?: ("main_image" | "detail_page" | "long_image")[];
            /**
             * Image Platform
             * @default
             */
            image_platform: string;
            /** Material Versions */
            material_versions?: components["schemas"]["FileVersionRef"][];
            /** Product Version */
            product_version?: string | null;
            /**
             * Video First Frame File Id
             * @default
             */
            video_first_frame_file_id: string;
            /**
             * Video Instruction
             * @default
             */
            video_instruction: string;
        };
        /** QuickPrepare */
        QuickPrepare: {
            /** Item Index */
            item_index?: number | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "copy" | "image" | "video";
            /** Outputs */
            outputs?: ("main_image" | "detail_page" | "long_image")[] | null;
            /** Version */
            version: number;
        };
        /** QuickSave */
        QuickSave: {
            draft: components["schemas"]["QuickDraft"];
            /** Version */
            version: number;
        };
        /** QuickState */
        QuickState: {
            /** Batches */
            batches?: components["schemas"]["QuickBatch"][];
            /** Confirmed Copy */
            confirmed_copy?: string | null;
            /** Confirmed Images */
            confirmed_images?: string | null;
            /** Current */
            current: {
                [key: string]: string | null;
            };
            draft: components["schemas"]["QuickDraft"];
            /** Pending Batch */
            pending_batch?: string | null;
            /** Step */
            step: number;
        };
        /** QuickSummary */
        QuickSummary: {
            /**
             * Conversation Id
             * Format: uuid
             */
            conversation_id: string;
            /**
             * Run Id
             * Format: uuid
             */
            run_id: string;
            /** Step */
            step: number;
            /** Title */
            title: string;
            /** Version */
            version: number;
        };
        /** QuickView */
        QuickView: {
            /**
             * Conversation Id
             * Format: uuid
             */
            conversation_id: string;
            /**
             * Run Id
             * Format: uuid
             */
            run_id: string;
            state: components["schemas"]["QuickState"];
            /** Step */
            step: number;
            /** Tasks */
            tasks: {
                [key: string]: components["schemas"]["TaskDetail"];
            };
            /** Title */
            title: string;
            /** Version */
            version: number;
        };
        /** Quote */
        Quote: {
            /** Agent Version */
            agent_version: string;
            /** Credits */
            credits: number;
            /** Input Digest */
            input_digest: string;
            /** Policy Versions */
            policy_versions: {
                [key: string]: string;
            };
            /** Price Version */
            price_version: string;
            /**
             * Spec Id
             * Format: uuid
             */
            spec_id: string;
            /** Spec Version */
            spec_version: string;
        };
        /** QuoteRequest */
        QuoteRequest: {
            /**
             * Agent Id
             * Format: uuid
             */
            agent_id: string;
            input: components["schemas"]["InputSnapshot"];
        };
        /** ReadyChecks */
        ReadyChecks: {
            /** Database */
            database: boolean;
            /** Storage */
            storage: boolean;
        };
        /** ReadyResponse */
        ReadyResponse: {
            checks: components["schemas"]["ReadyChecks"];
            /**
             * Mode
             * @enum {string}
             */
            mode: "mock" | "staging" | "production";
            /** Ready */
            ready: boolean;
            /** Test Only */
            test_only: boolean;
        };
        /** RegenerationConfirmation */
        RegenerationConfirmation: {
            /** Expected Credits */
            expected_credits: number;
            /** Expected Used */
            expected_used: number;
            /**
             * Source Task Id
             * Format: uuid
             */
            source_task_id: string;
        };
        /** RegenerationQuote */
        RegenerationQuote: {
            /** Credits */
            credits: number;
            /** Eligible */
            eligible: boolean;
            /** Free Regenerations Remaining */
            free_regenerations_remaining: number;
            /** Free Regenerations Used */
            free_regenerations_used: number;
            quote: components["schemas"]["Quote"];
        };
        /** RegenerationQuoteRequest */
        RegenerationQuoteRequest: {
            /**
             * Agent Id
             * Format: uuid
             */
            agent_id: string;
            input: components["schemas"]["InputSnapshot"];
        };
        /** RegenerationState */
        RegenerationState: {
            /** Free Regenerations Remaining */
            free_regenerations_remaining: number;
            /** Free Regenerations Used */
            free_regenerations_used: number;
            /**
             * Root Task Id
             * Format: uuid
             */
            root_task_id: string;
        };
        /** RegisterRequest */
        RegisterRequest: {
            /** Account */
            account: string;
            /**
             * Password
             * Format: password
             */
            password: string;
            /** Request Key */
            request_key: string;
        };
        /** RegistrationConfigUpdate */
        RegistrationConfigUpdate: {
            /** Amount */
            amount: number;
            /** Expected Version */
            expected_version: string | null;
            /** Policy Version */
            policy_version: string;
        };
        /** RegistrationConfigView */
        RegistrationConfigView: {
            /** Amount */
            amount: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Mode
             * @enum {string}
             */
            mode: "mock" | "staging" | "production";
            /** Policy Version */
            policy_version: string;
            /** Reason */
            reason: string;
            /** Test Only */
            test_only: boolean;
            /**
             * Version
             * Format: uuid
             */
            version: string;
        };
        /** ResetEvent */
        ResetEvent: {
            /**
             * Instruction
             * @default GET original persisted resources; never resubmit a task on reconnect.
             */
            instruction: string;
            /**
             * Reason
             * @default cursor_unavailable
             * @constant
             */
            reason: "cursor_unavailable";
            /**
             * Recovery Method
             * @default GET
             * @constant
             */
            recovery_method: "GET";
            /** Recovery Resources */
            recovery_resources?: string[];
        };
        /** ResolutionReceipt */
        ResolutionReceipt: {
            /**
             * Action
             * @enum {string}
             */
            action: "resume_original" | "confirm_failure" | "manual_close" | "settle";
            /** After Version */
            after_version: number;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Outcome */
            outcome: string;
            /**
             * Task Id
             * Format: uuid
             */
            task_id: string;
            /** Task Version */
            task_version: number;
        };
        /** ResolveInvestigation */
        ResolveInvestigation: {
            /**
             * Action
             * @enum {string}
             */
            action: "resume_original" | "confirm_failure" | "manual_close" | "settle";
            evidence: components["schemas"]["Evidence"];
            /** Expected Version */
            expected_version: number;
            /** Policy Version */
            policy_version: string;
            /** Reason */
            reason: string;
        };
        /** RevokeContentGrant */
        RevokeContentGrant: {
            /** Reason */
            reason: string;
        };
        /**
         * SettlementState
         * @enum {string}
         */
        SettlementState: "FROZEN" | "CONSUMED" | "RELEASED";
        /** SiteContent */
        SiteContent: {
            agent_descriptions: components["schemas"]["AgentDescriptions"];
            /** Process Steps */
            process_steps: string[];
            /** Product Intro */
            product_intro: string;
        };
        /** SiteContentUpdate */
        SiteContentUpdate: {
            content: components["schemas"]["SiteContent"];
            /** Expected Version */
            expected_version: number;
            /** Policy Version */
            policy_version: string;
            /** Policy Versions */
            policy_versions?: {
                [key: string]: string;
            };
        };
        /** SiteContentView */
        SiteContentView: {
            content: components["schemas"]["SiteContent"] | null;
            /** Content Ref */
            content_ref: string | null;
            /** Policy Version */
            policy_version: string;
            /** Policy Versions */
            policy_versions: {
                [key: string]: string;
            };
            /**
             * Status
             * @enum {string}
             */
            status: "draft" | "approved";
            /** Version */
            version: number;
        };
        /** SourceMaterial */
        SourceMaterial: {
            /** Action */
            action: "upload_again" | null;
            /** Available */
            available: boolean;
            file: components["schemas"]["FileVersionRef"];
        };
        /** SpecVersion */
        SpecVersion: {
            /**
             * Agent Id
             * Format: uuid
             */
            agent_id: string;
            /** Agent Version */
            agent_version: string;
            /**
             * Delivery Kind
             * @enum {string}
             */
            delivery_kind: "single" | "multiple" | "detail_images";
            /** Enabled */
            enabled: boolean;
            /** Name */
            name: string;
            parameter_schema: components["schemas"]["ParameterSchema"];
            /** Policy Versions */
            policy_versions: {
                [key: string]: string;
            };
            /**
             * Spec Id
             * Format: uuid
             */
            spec_id: string;
            /** Version */
            version: string;
        };
        /** StatisticsView */
        StatisticsView: {
            /**
             * Active In Trend
             * @default 0
             */
            active_in_trend: number;
            /**
             * Active Today
             * @default 0
             */
            active_today: number;
            /**
             * Active User Basis
             * @default generation_task_created
             * @constant
             */
            active_user_basis: "generation_task_created";
            /** Admin Granted Credits */
            admin_granted_credits: number;
            /** By Agent */
            by_agent?: components["schemas"]["AgentUsageView"][];
            /** Credits Consumed */
            credits_consumed: number;
            /** Credits Frozen */
            credits_frozen: number;
            /** Credits Released */
            credits_released: number;
            /** Daily Trend */
            daily_trend: components["schemas"]["DailyUsageView"][];
            /** Generated Count */
            generated_count: number;
            /**
             * Payment Revenue Status
             * @constant
             */
            payment_revenue_status: "not_supported";
            /**
             * Registered In Trend
             * @default 0
             */
            registered_in_trend: number;
            /**
             * Registered Today
             * @default 0
             */
            registered_today: number;
            /** Signup Credits */
            signup_credits: number;
            /** State Counts */
            state_counts?: {
                [key: string]: number;
            };
            /** Succeeded Count */
            succeeded_count: number;
            /** Success Rate */
            success_rate: number | null;
            /**
             * Success Rate Basis
             * @constant
             */
            success_rate_basis: "succeeded / (succeeded + failed + manually_closed)";
            /** Supplier Cost */
            supplier_cost: null;
            /**
             * Supplier Cost Status
             * @constant
             */
            supplier_cost_status: "unavailable";
            /**
             * Supplier Usage Status
             * @constant
             */
            supplier_usage_status: "unavailable";
            /** Terminal Count */
            terminal_count: number;
            /**
             * Total Users
             * @default 0
             */
            total_users: number;
            /** Trend Days */
            trend_days: number;
            /**
             * Trend Timezone
             * @constant
             */
            trend_timezone: "UTC";
            /**
             * Unsettled Count
             * @default 0
             */
            unsettled_count: number;
        };
        /** SubmitTaskRequest */
        SubmitTaskRequest: {
            /**
             * Agent Id
             * Format: uuid
             */
            agent_id: string;
            confirmed_quote: components["schemas"]["Quote"];
            /**
             * Conversation Id
             * Format: uuid
             */
            conversation_id: string;
            input: components["schemas"]["InputSnapshot"];
            regeneration?: components["schemas"]["RegenerationConfirmation"] | null;
        };
        /** TaskDetail */
        TaskDetail: {
            /**
             * Agent Id
             * Format: uuid
             */
            agent_id: string;
            /** Conversation Display Number */
            readonly conversation_display_number: string;
            /**
             * Conversation Id
             * Format: uuid
             */
            conversation_id: string;
            input: components["schemas"]["InputSnapshot"];
            /** Media */
            media?: {
                [key: string]: unknown;
            } | null;
            /** Policy Versions */
            policy_versions: {
                [key: string]: string;
            };
            regeneration?: components["schemas"]["RegenerationState"] | null;
            task: components["schemas"]["TaskView"];
        };
        /** TaskDiagnosticView */
        TaskDiagnosticView: {
            /** Account */
            account?: string | null;
            /**
             * Agent Id
             * Format: uuid
             */
            agent_id: string;
            /** Agent Version */
            agent_version: string;
            /** Conversation Id */
            conversation_id?: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Diagnostic Code */
            diagnostic_code: string | null;
            /** Elapsed Seconds */
            elapsed_seconds: number;
            /** External Submission Id */
            external_submission_id?: string | null;
            /** Fixed Credits */
            fixed_credits?: number | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Investigation Deadline */
            investigation_deadline: string | null;
            /** Investigation Owner */
            investigation_owner: string | null;
            /** Investigation Status */
            investigation_status: string | null;
            /** Price Version */
            price_version?: string | null;
            settlement_state: components["schemas"]["SettlementState"];
            /** Spec Version */
            spec_version?: string | null;
            state: components["schemas"]["TaskState"];
            /** State Version */
            state_version: number;
            /** Timeline */
            timeline?: components["schemas"]["TaskTimelineEvent"][];
            /** Updated At */
            updated_at?: string | null;
            /** Upstream Id */
            upstream_id?: string | null;
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
            /** Work Ids */
            work_ids?: string[];
        };
        /** TaskEventPayload */
        TaskEventPayload: {
            /**
             * Conversation Id
             * @default null
             */
            conversation_id: string | null;
            /**
             * Media Revision
             * @default null
             */
            media_revision: number | null;
            state: components["schemas"]["TaskState"];
            /** State Version */
            state_version: number;
            /**
             * Task Id
             * Format: uuid
             */
            task_id: string;
        };
        /**
         * TaskState
         * @enum {string}
         */
        TaskState: "SUBMITTED" | "QUEUED" | "SUBMITTING" | "RUNNING" | "INVESTIGATING" | "SAVING" | "SAVE_RECOVERY" | "SUCCEEDED" | "FAILED" | "MANUALLY_CLOSED";
        /** TaskTimelineEvent */
        TaskTimelineEvent: {
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            from_state: components["schemas"]["TaskState"] | null;
            /** State Version */
            state_version: number;
            to_state: components["schemas"]["TaskState"];
        };
        /** TaskView */
        TaskView: {
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Display Number */
            readonly display_number: string;
            /** Investigation Reason */
            investigation_reason: string | null;
            quote: components["schemas"]["Quote"];
            settlement_state: components["schemas"]["SettlementState"];
            state: components["schemas"]["TaskState"];
            /** State Version */
            state_version: number;
            /**
             * Task Id
             * Format: uuid
             */
            task_id: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            /** Work Ids */
            work_ids: string[];
        };
        /** TextDefaultModelUpdate */
        TextDefaultModelUpdate: {
            /** Expected Connection Revision */
            expected_connection_revision: number;
            /** Expected Revision */
            expected_revision: number;
            /**
             * Model Config Id
             * Format: uuid
             */
            model_config_id: string;
        };
        /** TextDefaultModelView */
        TextDefaultModelView: {
            /** Connection Revision */
            connection_revision: number;
            /**
             * Generation Policy Configured
             * @default false
             */
            generation_policy_configured: boolean;
            /** Model Config Id */
            model_config_id: string | null;
            /** Revision */
            revision: number;
        };
        /** TextModelCreate */
        TextModelCreate: {
            config: components["schemas"]["TextModelCreateFields"];
        };
        /** TextModelCreateFields */
        TextModelCreateFields: {
            /**
             * Api Key
             * Format: password
             */
            api_key: string;
            /** Base Url */
            base_url: string;
            /** Max Tokens */
            max_tokens?: number | null;
            /** Model */
            model: string;
            /** Name */
            name: string;
            /**
             * Provider
             * @default openai_chat
             * @constant
             */
            provider: "openai_chat";
            /** Reasoning Effort */
            reasoning_effort?: ("none" | "minimal" | "low" | "medium" | "high" | "xhigh" | "max") | null;
            /**
             * Supports Images
             * @default false
             */
            supports_images: boolean;
            /** Temperature */
            temperature?: number | null;
            /**
             * Timeout Seconds
             * @default 60
             */
            timeout_seconds: number;
        };
        /** TextModelPage */
        TextModelPage: {
            /** Items */
            items: components["schemas"]["TextModelView"][];
            /** Next Cursor */
            next_cursor?: string | null;
        };
        /** TextModelPatch */
        TextModelPatch: {
            /** Api Key */
            api_key?: string | null;
            /** Base Url */
            base_url?: string | null;
            /** Enabled */
            enabled?: boolean | null;
            /** Max Tokens */
            max_tokens?: number | null;
            /** Model */
            model?: string | null;
            /** Name */
            name?: string | null;
            /** Provider */
            provider?: "openai_chat" | null;
            /** Reasoning Effort */
            reasoning_effort?: ("none" | "minimal" | "low" | "medium" | "high" | "xhigh" | "max") | null;
            /** Supports Images */
            supports_images?: boolean | null;
            /** Temperature */
            temperature?: number | null;
            /** Timeout Seconds */
            timeout_seconds?: number | null;
        };
        /** TextModelUpdate */
        TextModelUpdate: {
            config: components["schemas"]["TextModelPatch"];
            /** Expected Revision */
            expected_revision: number;
        };
        /** TextModelView */
        TextModelView: {
            /** Base Url */
            base_url: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Enabled */
            enabled: boolean;
            /** Has Api Key */
            has_api_key: boolean;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Max Tokens */
            max_tokens: number | null;
            /** Model */
            model: string;
            /** Name */
            name: string;
            /** Provider */
            provider: string;
            /** Reasoning Effort */
            reasoning_effort?: ("none" | "minimal" | "low" | "medium" | "high" | "xhigh" | "max") | null;
            /** Revision */
            revision: number;
            /** Supports Images */
            supports_images: boolean;
            /** Temperature */
            temperature: number | null;
            /** Timeout Seconds */
            timeout_seconds: number;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** TextServiceConnectionUpdate */
        TextServiceConnectionUpdate: {
            /** Base Url */
            base_url: string;
            /** Expected Revision */
            expected_revision: number;
            /** Service Key */
            service_key?: string | null;
        };
        /** TextServiceConnectionView */
        TextServiceConnectionView: {
            /** Base Url */
            base_url: string | null;
            /** Has Service Key */
            has_service_key: boolean;
            /** Revision */
            revision: number;
            /** Updated At */
            updated_at: string | null;
        };
        /** TransientFragment */
        TransientFragment: {
            /**
             * Replayable
             * @default false
             * @constant
             */
            replayable: false;
            /**
             * Task Id
             * Format: uuid
             */
            task_id: string;
            /**
             * Test Only
             * @default true
             * @constant
             */
            test_only: true;
            /** Text */
            text: string;
        };
        /**
         * UserRole
         * @enum {string}
         */
        UserRole: "user" | "admin";
        /** VideoAudioUpdate */
        VideoAudioUpdate: {
            /** Enabled */
            enabled: boolean;
            /** Expected Configuration Revision */
            expected_configuration_revision: number;
            /** Expected Revision */
            expected_revision: number;
        };
        /** VideoConfirm */
        VideoConfirm: {
            /** Plan Version */
            plan_version: number;
        };
        /** VideoInputs */
        VideoInputs: {
            /** Text */
            text: string;
        };
        /** VideoModelUpdate */
        VideoModelUpdate: {
            /**
             * Adapter
             * @enum {string}
             */
            adapter: "openai_chat" | "seedance" | "wan" | "openai_vision";
            /** Api Key */
            api_key?: string | null;
            /** Base Url */
            base_url?: string | null;
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
            /** Expected Configuration Revision */
            expected_configuration_revision: number;
            /** Expected Profile Id */
            expected_profile_id: string | null;
            /** Expected Profile Version */
            expected_profile_version: number | null;
            /** Expected Revision */
            expected_revision: number;
            /** Max Segment Seconds */
            max_segment_seconds?: number | null;
            /** Model */
            model?: string | null;
        };
        /** VideoOptionsView */
        VideoOptionsView: {
            /** Aspect Ratios */
            aspect_ratios: ("9:16" | "16:9" | "1:1" | "4:5" | "3:4" | "4:3" | "3:2" | "2:3")[];
            /** Default Duration */
            default_duration: number;
            /** Duration Tiers */
            duration_tiers: number[];
        };
        /** VideoPlanPatch */
        VideoPlanPatch: {
            /** Music Direction */
            music_direction?: string | null;
            /** Shot Texts */
            shot_texts?: components["schemas"]["VideoShotTextPatch"][] | null;
        };
        /** VideoPlanRevision */
        VideoPlanRevision: {
            /** Instruction */
            instruction?: string | null;
            patch?: components["schemas"]["VideoPlanPatch"] | null;
            /** Plan Version */
            plan_version: number;
        };
        /** VideoShotTextPatch */
        VideoShotTextPatch: {
            /** Action */
            action?: string | null;
            /** Camera */
            camera?: string | null;
            /** Content */
            content?: string | null;
            /** Shot Id */
            shot_id: string;
            /** Shot Size */
            shot_size?: string | null;
            /** Subtitle Text */
            subtitle_text?: string | null;
            /** Voiceover Text */
            voiceover_text?: string | null;
        };
        /** WorkDetail */
        WorkDetail: {
            /**
             * Conversation Id
             * Format: uuid
             */
            conversation_id: string;
            /** Conversation Title */
            conversation_title?: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Items */
            items: components["schemas"]["WorkItemView"][];
            /**
             * Kind
             * @enum {string}
             */
            kind: "copy" | "image" | "video";
            /**
             * Message Id
             * Format: uuid
             */
            message_id: string;
            /** Name */
            name?: string | null;
            source: components["schemas"]["WorkSource"];
            /**
             * Task Id
             * Format: uuid
             */
            task_id: string;
            /** Warnings */
            warnings?: string[];
            /**
             * Work Id
             * Format: uuid
             */
            work_id: string;
        };
        /** WorkItemView */
        WorkItemView: {
            /** Actual Bytes */
            actual_bytes: number;
            /** Content Url */
            content_url: string;
            /**
             * File Id
             * Format: uuid
             */
            file_id: string;
            /** File Version */
            file_version: string;
            /** Item Key */
            item_key: string;
            /** Media Type */
            media_type: string;
            /** Text */
            text: string | null;
        };
        /** WorkPage */
        WorkPage: {
            /** Items */
            items: components["schemas"]["WorkView"][];
            /** Next Cursor */
            next_cursor: string | null;
            /** Page */
            page?: number | null;
            /** Page Size */
            page_size?: number | null;
            /** Total */
            total?: number | null;
        };
        /**
         * WorkSource
         * @description Read-only original input. Reuse requires a new quote and a new intent key.
         */
        WorkSource: {
            /**
             * Agent Id
             * Format: uuid
             */
            agent_id: string;
            /** Conversation Display Number */
            readonly conversation_display_number: string;
            /**
             * Conversation Id
             * Format: uuid
             */
            conversation_id: string;
            /**
             * Credit Reservation Id
             * Format: uuid
             */
            credit_reservation_id: string;
            input: components["schemas"]["InputSnapshot"];
            /** Ledger Ids */
            ledger_ids: string[];
            /** Materials */
            materials: components["schemas"]["SourceMaterial"][];
            /** Media */
            media?: {
                [key: string]: unknown;
            } | null;
            /** Policy Versions */
            policy_versions: {
                [key: string]: string;
            };
            regeneration?: components["schemas"]["RegenerationState"] | null;
            /**
             * Requires New Quote
             * @default true
             * @constant
             */
            requires_new_quote: true;
            task: components["schemas"]["TaskView"];
        };
        /** WorkView */
        WorkView: {
            /**
             * Conversation Id
             * Format: uuid
             */
            conversation_id: string;
            /** Conversation Title */
            conversation_title?: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Items */
            items: components["schemas"]["WorkItemView"][];
            /**
             * Kind
             * @enum {string}
             */
            kind: "copy" | "image" | "video";
            /**
             * Message Id
             * Format: uuid
             */
            message_id: string;
            /** Name */
            name?: string | null;
            /**
             * Task Id
             * Format: uuid
             */
            task_id: string;
            /** Warnings */
            warnings?: string[];
            /**
             * Work Id
             * Format: uuid
             */
            work_id: string;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    get_account: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AccountView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_ledger: {
        parameters: {
            query?: {
                cursor?: string | null;
                limit?: number;
                start_time?: string | null;
                end_time?: string | null;
                page?: number | null;
            };
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AccountLedgerPage"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_agents: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AgentVersion"][];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    publish_agent: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path?: never;
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AgentDraft"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AgentVersion"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_list_audit: {
        parameters: {
            query?: {
                cursor?: string | null;
                limit?: number;
                action?: string | null;
                actor_id?: string | null;
                object_id?: string | null;
                q?: string | null;
                page?: number | null;
            };
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NumberedPage_AuditView_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_audit_summary: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdminAuditSummary"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_list_content_grants: {
        parameters: {
            query?: {
                cursor?: string | null;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CursorPage_ContentGrantView_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_grant_content_access: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path?: never;
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ContentGrantRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ContentGrantView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_revoke_content_grant: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                id: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RevokeContentGrant"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ContentGrantView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_read_content: {
        parameters: {
            query: {
                reason: string;
            };
            header?: never;
            path: {
                resource_type: "message" | "work" | "file" | "material" | "conversation" | "task" | "product_version";
                id: string;
            };
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuditedContent"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_download_content: {
        parameters: {
            query: {
                reason: string;
            };
            header?: {
                Range?: string | null;
            };
            path: {
                resource_type: "file" | "material";
                id: string;
            };
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/octet-stream": string;
                };
            };
            /** @description Partial Content */
            206: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/octet-stream": string;
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Requested Range Not Satisfiable */
            416: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_grant_credits: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path?: never;
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreditGrantRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CreditGrantView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_investigation_alerts: {
        parameters: {
            query?: {
                cursor?: string | null;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CursorPage_AlertView_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_investigations: {
        parameters: {
            query?: {
                cursor?: string | null;
                owner?: string | null;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CursorPage_InvestigationView_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_investigation: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: string;
            };
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InvestigationView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    assign_investigation: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                task_id: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AssignInvestigation"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InvestigationView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_list_ledger: {
        parameters: {
            query?: {
                cursor?: string | null;
                limit?: number;
                q?: string | null;
                page?: number | null;
            };
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NumberedPage_AdminLedgerEntryView_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_ledger_summary: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdminLedgerSummary"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_list_managed_users: {
        parameters: {
            query?: {
                cursor?: string | null;
                limit?: number;
                status?: ("active" | "disabled") | null;
                q?: string | null;
                page?: number | null;
            };
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NumberedPage_ManagedUserView_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_managed_user: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ManagedUserView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_delete_managed_user: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                id: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ManagedUserDelete"];
            };
        };
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_update_managed_user: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                id: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ManagedUserUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ManagedUserView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_adjust_managed_credits: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                id: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreditAdjustment"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CreditAdjustmentReceipt"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_reset_managed_password: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                id: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ManagedPasswordReset"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ManagedUserView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_image_models: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ImageModelsView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_save_image_models: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path?: never;
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ImageModelsUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ImageModelsView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_video_audio: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_save_video_audio: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path?: never;
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VideoAudioUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_video_models: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_save_video_model: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                role: "planner" | "video" | "visual";
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VideoModelUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_media_connection: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                kind: "image" | "video";
            };
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaConnectionView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_save_media_connection: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                kind: "image" | "video";
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MediaConnectionUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaConnectionView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_media_resources: {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
            };
            header?: never;
            path: {
                kind: "image" | "video";
                resource: string;
            };
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_create_media_resource: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                kind: "image" | "video";
                resource: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MediaResourceWrite"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_update_media_singleton: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                kind: "image" | "video";
                resource: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MediaResourceWrite"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_media_resource: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                kind: "image" | "video";
                resource: string;
                config_id: string;
            };
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_update_media_resource: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                kind: "image" | "video";
                resource: string;
                config_id: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MediaResourceWrite"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_get_parameter_config: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ParameterConfigView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_update_parameter_config: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path?: never;
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ParameterConfigUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ParameterConfigView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_get_registration_credit_config: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RegistrationConfigView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_update_registration_credit_config: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path?: never;
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RegistrationConfigUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RegistrationConfigView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_site_cases: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdminCaseView"][];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    publish_site_case: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path?: never;
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CasePublish"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdminCaseView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    withdraw_site_case: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                case_id: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CaseWithdraw"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdminCaseView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_site_content: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SiteContentView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    update_site_content: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path?: never;
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SiteContentUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SiteContentView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_statistics: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StatisticsView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_list_tasks: {
        parameters: {
            query?: {
                cursor?: string | null;
                limit?: number;
                state?: components["schemas"]["TaskState"] | null;
                user_id?: string | null;
                q?: string | null;
                agent_id?: string | null;
                page?: number | null;
            };
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NumberedPage_TaskDiagnosticView_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_tasks_summary: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdminTasksSummary"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_task_diagnostics: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TaskDiagnosticView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    open_investigation: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                id: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OpenInvestigation"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InvestigationView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    resolve_investigation: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                id: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ResolveInvestigation"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ResolutionReceipt"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_text_default_model: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TextDefaultModelView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_save_text_default_model: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path?: never;
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TextDefaultModelUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TextDefaultModelView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_text_models: {
        parameters: {
            query?: {
                cursor?: string | null;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TextModelPage"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_create_text_model: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path?: never;
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TextModelCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TextModelView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_text_model: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                config_id: string;
            };
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TextModelView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_update_text_model: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                config_id: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TextModelUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TextModelView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_text_service_connection: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TextServiceConnectionView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_save_text_service_connection: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path?: never;
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TextServiceConnectionUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TextServiceConnectionView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_list_users: {
        parameters: {
            query?: {
                cursor?: string | null;
                limit?: number;
                status?: ("active" | "disabled") | null;
                q?: string | null;
            };
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CursorPage_AdminUserView_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_users_summary: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdminUsersSummary"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_user_account: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AccountView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admin_user_ledger: {
        parameters: {
            query?: {
                cursor?: string | null;
                limit?: number;
                page?: number | null;
            };
            header?: never;
            path: {
                id: string;
            };
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NumberedPage_LedgerEntryView_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    set_account_status: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                id: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AccountStatusRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AccountStatusReceipt"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    receive_agent_callback: {
        parameters: {
            query?: never;
            header: {
                /** @description TEST_ONLY mock-v1 raw-body HMAC-SHA256 */
                "X-Mock-Signature": string;
            };
            path: {
                agent_id: string;
                version: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                /** @description Exact signed mock-v1 event bytes; no caller-verified DTO */
                "application/json": string;
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EventReceipt"];
                };
            };
            /** @description Unverified or disabled protocol */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Identity or replay conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Callback too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_agents: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AgentVersion"][];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    prepare_prompt: {
        parameters: {
            query?: never;
            header: {
                /** @description request_key is carried only in this required Idempotency-Key header. Reuse the key for the same draft request to replay its completed result; reusing it with different input returns 409. */
                "Idempotency-Key": string;
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path?: never;
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AssistRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssistProposal"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Gateway Timeout */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    auth_login: {
        parameters: {
            query?: never;
            header: {
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LoginRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    auth_logout: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path?: never;
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    auth_change_password: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path?: never;
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PasswordChangeRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    auth_register: {
        parameters: {
            query?: never;
            header: {
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RegisterRequest"];
            };
        };
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthView"];
                };
            };
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_conversations: {
        parameters: {
            query?: {
                cursor?: string | null;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CursorPage_ConversationSummary_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_conversation: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path?: never;
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ConversationCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConversationSummary"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_conversation: {
        parameters: {
            query?: {
                task_cursor?: string | null;
                message_cursor?: string | null;
                limit?: number;
            };
            header?: never;
            path: {
                id: string;
            };
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConversationView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    events_stream: {
        parameters: {
            query?: {
                after?: string | null;
            };
            header?: {
                "Last-Event-ID"?: string | null;
            };
            path?: never;
            cookie: {
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Native SSE: task.updated, reset, TEST_ONLY transient_fragment. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "text/event-stream": string;
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    upload_file: {
        parameters: {
            query: {
                display_name: string;
            };
            header: {
                "Content-Type": string;
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path?: never;
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "image/jpeg": string;
                "image/png": string;
                "image/webp": string;
                "video/mp4": string;
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FileVersionRef"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Requested Range Not Satisfiable */
            416: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    read_file_content: {
        parameters: {
            query?: never;
            header?: {
                Range?: string | null;
            };
            path: {
                file_id: string;
            };
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/octet-stream": string;
                };
            };
            /** @description Partial Content */
            206: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/octet-stream": string;
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Requested Range Not Satisfiable */
            416: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    delete_material: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                id: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DeleteRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DeleteReceipt"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    health_live: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LiveResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    health_ready: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReadyResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReadyResponse"];
                };
            };
        };
    };
    get_profile: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProfileView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    update_profile: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path?: never;
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProfileUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProfileView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_product_version: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path?: never;
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProductVersionCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProductVersionView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_product_version: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                version: string;
            };
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProductVersionView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_quick_generation: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuickSummary"][];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_quick_generation: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path?: never;
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["QuickCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuickView"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_quick_generation: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuickView"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    save_quick_generation: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                id: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["QuickSave"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuickView"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    advance_quick_generation: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                id: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["QuickAdvance"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuickView"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    cancel_quick_generation_batch: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                id: string;
                batch_id: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuickView"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    submit_quick_generation: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                id: string;
                batch_id: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuickView"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    prepare_quick_generation: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                id: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["QuickPrepare"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuickView"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    quote_generation: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path?: never;
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["QuoteRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Quote"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    public_site_cases: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PublicCaseView"][];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    public_site_copy: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                case_id: string;
                copy_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    public_site_content: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PublicSiteView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_tasks: {
        parameters: {
            query?: {
                conversation_id?: string | null;
                cursor?: string | null;
                limit?: number;
                task_type?: "ordinary" | null;
            };
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CursorPage_TaskView_"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Payment Required */
            402: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    admit_task: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path?: never;
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SubmitTaskRequest"];
            };
        };
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdmissionResult"];
                };
            };
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdmissionResult"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Payment Required */
            402: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_task: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TaskDetail"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Payment Required */
            402: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    delete_task_history: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                id: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Payment Required */
            402: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    task_history: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TaskDetail"][];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Payment Required */
            402: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    quote_task_regeneration: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                id: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RegenerationQuoteRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RegenerationQuote"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Payment Required */
            402: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    release_failed_task: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                id: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TaskView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Payment Required */
            402: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    retry_failed_task: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                id: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdmissionResult"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Payment Required */
            402: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    confirm_video_plan: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                id: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VideoConfirm"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    supplement_video_inputs: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                id: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VideoInputs"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    revise_video_plan: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                id: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VideoPlanRevision"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_own_investigation: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: string;
            };
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OwnerView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    video_options: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["VideoOptionsView"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_works: {
        parameters: {
            query?: {
                kind?: ("copy" | "image" | "video") | null;
                cursor?: string | null;
                limit?: number;
                q?: string | null;
                page?: number | null;
            };
            header?: never;
            path?: never;
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkPage"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_work: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie: {
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkDetail"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    delete_work: {
        parameters: {
            query?: never;
            header: {
                /** @description Required token bound to this session and csrf_token cookie; omission or mismatch returns 403. */
                "X-CSRF-Token": string;
                /** @description Required exact allowlisted Origin; browsers send this automatically. Do not set Origin in frontend JavaScript. */
                origin: string;
                /** @description Required literal platform; omission or mismatch returns 403. */
                "X-Requested-With": string;
            };
            path: {
                id: string;
            };
            cookie: {
                /** @description Required session-bound CSRF cookie; omission or mismatch returns 403. */
                csrf_token: string;
                /** @description Required Secure HttpOnly session cookie; omission or invalid session returns 401. */
                session: string;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DeleteRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DeleteReceipt"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
}
