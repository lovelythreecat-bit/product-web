// Generated from contracts/openapi.json. Do not edit.
export interface paths {
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
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
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
        /** AuthView */
        AuthView: {
            profile: components["schemas"]["ProfileView"];
            /** Replayed */
            replayed: boolean;
        };
        /** CursorPage[TaskView] */
        CursorPage_TaskView_: {
            /** Items */
            items: components["schemas"]["TaskView"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /**
         * ErrorCode
         * @enum {string}
         */
        ErrorCode: "INPUT_INVALID" | "SPEC_DISABLED" | "QUOTE_STALE" | "IDEMPOTENCY_CONFLICT" | "INSUFFICIENT_CREDITS" | "CAPACITY_INSUFFICIENT" | "FEATURE_NOT_ENABLED" | "RATE_LIMITED" | "UNAUTHENTICATED" | "FORBIDDEN" | "NOT_FOUND" | "METHOD_NOT_ALLOWED" | "INTERNAL_ERROR";
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
        /**
         * SettlementState
         * @enum {string}
         */
        SettlementState: "FROZEN" | "CONSUMED" | "RELEASED";
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
        /**
         * UserRole
         * @enum {string}
         */
        UserRole: "user" | "admin";
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
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
}
