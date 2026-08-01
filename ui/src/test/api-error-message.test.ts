import { AxiosError, AxiosHeaders } from 'axios'
import { describe, expect, it } from 'vitest'
import { extractApiErrorMessage } from '../api/client'

function axiosErrorWith(status: number, data: unknown): AxiosError {
  const error = new AxiosError(`Request failed with status code ${status}`)
  error.response = {
    status,
    statusText: '',
    data,
    headers: new AxiosHeaders(),
    config: { headers: new AxiosHeaders() },
  }
  return error
}

describe('extractApiErrorMessage', () => {
  it('returns a plain string detail unchanged', () => {
    const error = axiosErrorWith(404, { detail: 'Project not found' })

    expect(extractApiErrorMessage(error)).toBe('Project not found')
  })

  it('explains a FastAPI validation failure instead of the opaque status text', () => {
    // Previously this fell through to "Request failed with status code 422",
    // which told the user nothing about which field was rejected.
    const error = axiosErrorWith(422, {
      detail: [
        {
          type: 'extra_forbidden',
          loc: ['body', 'content_json'],
          msg: 'Extra inputs are not permitted',
        },
      ],
    })

    const message = extractApiErrorMessage(error)

    expect(message).toContain('content_json')
    expect(message).toContain('Extra inputs are not permitted')
    expect(message).not.toBe('Request failed with status code 422')
  })

  it('joins several validation issues', () => {
    const error = axiosErrorWith(422, {
      detail: [
        { loc: ['body', 'title'], msg: 'Field required' },
        { loc: ['body', 'project_id'], msg: 'Input should be a valid integer' },
      ],
    })

    const message = extractApiErrorMessage(error)

    expect(message).toContain('title: Field required')
    expect(message).toContain('project_id: Input should be a valid integer')
  })

  it('drops the body scope from nested locations', () => {
    const error = axiosErrorWith(422, {
      detail: [{ loc: ['body', 'steps', 0, 'action'], msg: 'Field required' }],
    })

    expect(extractApiErrorMessage(error)).toBe('steps.0.action: Field required')
  })

  it('falls back when the payload carries nothing usable', () => {
    const error = axiosErrorWith(500, {})

    expect(extractApiErrorMessage(error, 'Could not save document')).toBe(
      'Request failed with status code 500',
    )
  })
})
