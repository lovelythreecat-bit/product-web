// Generated from contracts/openapi.json. Do not edit.
export interface paths {
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
        /**
         * SettlementState
         * @enum {string}
         */
        SettlementState: "FROZEN" | "CONSUMED" | "RELEASED";
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
}
