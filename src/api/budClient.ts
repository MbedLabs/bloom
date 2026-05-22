import axios from 'axios'

const budBaseUrl = window.runtimeConfig?.BUD_APP_URL
    || import.meta.env.VITE_TESTSTATION_APP_URL
    || 'http://localhost:3000'

const budApi = axios.create({
    baseURL: budBaseUrl,
    headers: { 'Content-Type': 'application/json' },
})

export interface BudTestRun {
    id: number
    name: string
    status: string
    test_case_list: string
    total_tests: number
    passed_tests: number
    failed_tests: number
    skipped_tests: number
    duration_seconds: number | null
    created_at: string
    started_at: string | null
    completed_at: string | null
    runner_account: string | null
}

export interface BudTestResult {
    id: number
    test_class: string
    test_method: string
    test_name?: string
    passed: boolean
    status?: string
    duration_seconds: number
    error_message: string | null
    traceback: string | null
    assertions: Record<string, unknown>[] | null
    test_metadata: Record<string, unknown> | null
    created_at: string
    test_run_id: number | null
    artifacts?: string[]
}

export const budTestRunsApi = {
    list: async (params?: { status?: string; limit?: number }) => {
        const response = await budApi.get<{ runs: BudTestRun[]; total: number }>(
            '/api/test-runs',
            { params },
        )
        return response.data
    },
}

export const budResultsApi = {
    list: async (testRunId: number) => {
        const response = await budApi.get<BudTestResult[]>(
            `/api/test-runs/results/${testRunId}`,
        )
        return response.data
    },
}
