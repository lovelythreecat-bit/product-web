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
    "/api/v1/admin/prices": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Admin Prices */
        get: operations["admin_prices"];
        put?: never;
        /** Publish Price */
        post: operations["publish_price"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
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
    "/api/v1/admin/specs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Admin Specs */
        get: operations["admin_specs"];
        put?: never;
        /** Publish Spec */
        post: operations["publish_spec"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
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
    "/api/v1/agents/{agent_id}/specs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Specs */
        get: operations["list_agent_specs"];
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
        /** AdminUserView */
        AdminUserView: {
            /** Account Normalized */
            account_normalized: string;
            /** Auth Version */
            auth_version: number;
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
            /** Nickname */
            nickname: string | null;
            /**
             * Role
             * @enum {string}
             */
            role: "user" | "admin";
            /**
             * Status
             * @enum {string}
             */
            status: "active" | "disabled";
        };
        /** AdmissionResult */
        AdmissionResult: {
            /** Replayed */
            replayed: boolean;
            task: components["schemas"]["TaskView"];
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
            /** Reason */
            reason: string;
            /** Secret Ref */
            secret_ref?: string | null;
            /** Test Only */
            test_only: boolean;
            /** Version */
            version: string;
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
             * @constant
             */
            test_only: true;
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
            /**
             * Spec Id
             * Format: uuid
             */
            spec_id: string;
            /** Spec Version */
            spec_version: string;
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
            /** Title */
            title: string;
        };
        /** ConversationView */
        ConversationView: {
            conversation: components["schemas"]["ConversationSummary"];
            messages: components["schemas"]["CursorPage_MessageView_"];
            tasks: components["schemas"]["CursorPage_TaskView_"];
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
        /** CursorPage[AuditView] */
        CursorPage_AuditView_: {
            /** Items */
            items: components["schemas"]["AuditView"][];
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
        /** CursorPage[LedgerEntryView] */
        CursorPage_LedgerEntryView_: {
            /** Items */
            items: components["schemas"]["LedgerEntryView"][];
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
        /** CursorPage[TaskDiagnosticView] */
        CursorPage_TaskDiagnosticView_: {
            /** Items */
            items: components["schemas"]["TaskDiagnosticView"][];
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
        /** CursorPage[WorkView] */
        CursorPage_WorkView_: {
            /** Items */
            items: components["schemas"]["WorkView"][];
            /** Next Cursor */
            next_cursor: string | null;
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
        ErrorCode: "MATERIAL_UNAVAILABLE" | "INPUT_INVALID" | "SPEC_DISABLED" | "QUOTE_STALE" | "IDEMPOTENCY_CONFLICT" | "INSUFFICIENT_CREDITS" | "CAPACITY_INSUFFICIENT" | "FEATURE_NOT_ENABLED" | "RATE_LIMITED" | "UNAUTHENTICATED" | "FORBIDDEN" | "NOT_FOUND" | "METHOD_NOT_ALLOWED" | "INTERNAL_ERROR";
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
        /** LedgerBalances */
        LedgerBalances: {
            /** Available */
            available: number;
            /** Consumed */
            consumed: number;
            /** Frozen */
            frozen: number;
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
        /** PriceDraft */
        PriceDraft: {
            /** Credits */
            credits: number;
            /** Enabled */
            enabled: boolean;
            /** Expected Version */
            expected_version?: string | null;
            /** Policy Version */
            policy_version: string;
            /** Reason */
            reason: string;
            /**
             * Spec Id
             * Format: uuid
             */
            spec_id: string;
            /** Version */
            version: string;
        };
        /** PriceVersion */
        PriceVersion: {
            /** Credits */
            credits: number;
            /** Enabled */
            enabled: boolean;
            /** Policy Version */
            policy_version: string;
            /**
             * Spec Id
             * Format: uuid
             */
            spec_id: string;
            /** Version */
            version: string;
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
            /** Bio */
            bio?: string | null;
            /** Nickname */
            nickname?: string | null;
        };
        /** ProfileView */
        ProfileView: {
            /** Account */
            account: string;
            /** Bio */
            bio: string | null;
            /** Nickname */
            nickname: string | null;
            role: components["schemas"]["UserRole"];
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
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
            input: components["schemas"]["InputSnapshot"];
            /**
             * Spec Id
             * Format: uuid
             */
            spec_id: string;
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
            /** Reason */
            reason: string;
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
        /** SourceMaterial */
        SourceMaterial: {
            /** Action */
            action: "upload_again" | null;
            /** Available */
            available: boolean;
            file: components["schemas"]["FileVersionRef"];
        };
        /** SpecDraft */
        SpecDraft: {
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
            /** Expected Version */
            expected_version?: string | null;
            /** Name */
            name: string;
            parameter_schema: components["schemas"]["ParameterSchema"];
            /** Policy Versions */
            policy_versions: {
                [key: string]: string;
            };
            /** Reason */
            reason: string;
            /**
             * Spec Id
             * Format: uuid
             */
            spec_id: string;
            /** Version */
            version: string;
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
            /** Admin Granted Credits */
            admin_granted_credits: number;
            /** Credits Consumed */
            credits_consumed: number;
            /** Generated Count */
            generated_count: number;
            /**
             * Payment Revenue Status
             * @constant
             */
            payment_revenue_status: "not_supported";
            /** Signup Credits */
            signup_credits: number;
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
        };
        /** TaskDetail */
        TaskDetail: {
            /**
             * Agent Id
             * Format: uuid
             */
            agent_id: string;
            /**
             * Conversation Id
             * Format: uuid
             */
            conversation_id: string;
            input: components["schemas"]["InputSnapshot"];
            /** Policy Versions */
            policy_versions: {
                [key: string]: string;
            };
            task: components["schemas"]["TaskView"];
        };
        /** TaskDiagnosticView */
        TaskDiagnosticView: {
            /**
             * Agent Id
             * Format: uuid
             */
            agent_id: string;
            /** Agent Version */
            agent_version: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Diagnostic Code */
            diagnostic_code: string | null;
            /** Elapsed Seconds */
            elapsed_seconds: number;
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
            settlement_state: components["schemas"]["SettlementState"];
            state: components["schemas"]["TaskState"];
            /** State Version */
            state_version: number;
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
        };
        /** TaskEventPayload */
        TaskEventPayload: {
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
        /** TaskView */
        TaskView: {
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
            /** Work Ids */
            work_ids: string[];
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
        /** WorkDetail */
        WorkDetail: {
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
            source: components["schemas"]["WorkSource"];
            /**
             * Task Id
             * Format: uuid
             */
            task_id: string;
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
            /** Policy Versions */
            policy_versions: {
                [key: string]: string;
            };
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
            /**
             * Task Id
             * Format: uuid
             */
            task_id: string;
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
                    "application/json": components["schemas"]["CursorPage_LedgerEntryView_"];
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
                    "application/json": components["schemas"]["CursorPage_AuditView_"];
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
    admin_prices: {
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
                    "application/json": components["schemas"]["PriceVersion"][];
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
    publish_price: {
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
                "application/json": components["schemas"]["PriceDraft"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PriceVersion"];
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
    admin_specs: {
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
                    "application/json": components["schemas"]["SpecVersion"][];
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
    publish_spec: {
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
                "application/json": components["schemas"]["SpecDraft"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SpecVersion"];
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
                    "application/json": components["schemas"]["CursorPage_TaskDiagnosticView_"];
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
    admin_list_users: {
        parameters: {
            query?: {
                cursor?: string | null;
                limit?: number;
                status?: ("active" | "disabled") | null;
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
                    "application/json": components["schemas"]["CursorPage_LedgerEntryView_"];
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
    list_agent_specs: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                agent_id: string;
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
                    "application/json": components["schemas"]["SpecVersion"][];
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
    list_tasks: {
        parameters: {
            query?: {
                conversation_id?: string | null;
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
    list_works: {
        parameters: {
            query?: {
                kind?: ("copy" | "image" | "video") | null;
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
                    "application/json": components["schemas"]["CursorPage_WorkView_"];
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
