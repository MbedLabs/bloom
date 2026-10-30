import { getSchema } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { describe, expect, it } from 'vitest'

import { QUOTE_CONTEXT, findQuote, plainText, quoteFor, rangeFor } from '../lib/textQuote'

const schema = getSchema([StarterKit])

/** A document with one paragraph per given text. */
function doc(...paragraphs: string[]) {
  return schema.nodeFromJSON({
    type: 'doc',
    content: paragraphs.map(text => ({ type: 'paragraph', content: text ? [{ type: 'text', text }] : [] })),
  })
}

const twoBrakes = doc('The brake shall engage.', 'The brake shall release.')

describe('the plain text of a document', () => {
  it('joins text blocks with one line break and maps each character to its position', () => {
    const { text, positions } = plainText(twoBrakes)
    expect(text).toBe('The brake shall engage.\nThe brake shall release.')
    expect(positions).toHaveLength(text.length)
    expect(positions[0]).toBe(1)
    expect(twoBrakes.textBetween(positions[4], positions[8] + 1)).toBe('brake')
    expect(twoBrakes.textBetween(positions[28], positions[32] + 1)).toBe('brake')
  })
})

describe('quoteFor', () => {
  it('quotes the selected passage with the text before and after it', () => {
    expect(quoteFor(twoBrakes, 5, 10)).toEqual({
      exact: 'brake',
      prefix: 'The ',
      suffix: ' shall engage.\nThe brake shall release.',
    })
  })

  it('quotes a passage in the second block with the first block as its prefix', () => {
    expect(quoteFor(twoBrakes, 30, 35)).toEqual({
      exact: 'brake',
      prefix: 'The brake shall engage.\nThe ',
      suffix: ' shall release.',
    })
  })

  it(`keeps at most ${QUOTE_CONTEXT} characters of context on each side`, () => {
    const before = 'a'.repeat(100)
    const after = 'b'.repeat(100)
    const long = doc(`${before}passage${after}`)
    const quote = quoteFor(long, 101, 108)
    expect(quote?.exact).toBe('passage')
    expect(quote?.prefix).toBe('a'.repeat(QUOTE_CONTEXT))
    expect(quote?.suffix).toBe('b'.repeat(QUOTE_CONTEXT))
  })

  it('gives no quote for an empty or blank selection', () => {
    expect(quoteFor(twoBrakes, 5, 5)).toBeNull()
    expect(quoteFor(twoBrakes, 4, 5)).toBeNull()
  })
})

describe('findQuote', () => {
  const { text } = plainText(twoBrakes)

  it('finds the occurrence whose prefix and suffix match', () => {
    expect(findQuote(text, { exact: 'brake', prefix: 'The ', suffix: ' shall engage.' })).toEqual({ start: 4, end: 9 })
    expect(findQuote(text, { exact: 'brake', prefix: 'engage.\nThe ', suffix: ' shall release.' })).toEqual({ start: 28, end: 33 })
  })

  it('prefers the matching suffix over the first occurrence when the prefixes are equal', () => {
    expect(findQuote(text, { exact: 'brake', prefix: 'The ', suffix: ' shall release.' })).toEqual({ start: 28, end: 33 })
  })

  it('takes the first occurrence when the context does not tell them apart', () => {
    expect(findQuote(text, { exact: 'brake', prefix: '', suffix: '' })).toEqual({ start: 4, end: 9 })
  })

  it('still finds a passage whose context changed', () => {
    expect(findQuote(text, { exact: 'release', prefix: 'unrelated ', suffix: ' elsewhere' })).toEqual({ start: 40, end: 47 })
  })

  it('reports a missing or empty passage as gone', () => {
    expect(findQuote(text, { exact: 'accelerate', prefix: 'The ', suffix: '.' })).toBeNull()
    expect(findQuote(text, { exact: '', prefix: 'The ', suffix: '.' })).toBeNull()
  })
})

describe('rangeFor', () => {
  it('maps a quote back to the document range it covers', () => {
    const second = quoteFor(twoBrakes, 30, 35)!
    expect(rangeFor(twoBrakes, second)).toEqual({ from: 30, to: 35 })
    const first = quoteFor(twoBrakes, 5, 10)!
    expect(rangeFor(twoBrakes, first)).toEqual({ from: 5, to: 10 })
  })

  it('maps a quote across blocks to the range from its first to its last character', () => {
    const quote = quoteFor(twoBrakes, 17, 30)!
    expect(quote.exact).toBe('engage.\nThe ')
    const range = rangeFor(twoBrakes, quote)!
    expect(range).toEqual({ from: 17, to: 30 })
  })

  it('finds the passage again after the text before it changed', () => {
    const quote = quoteFor(twoBrakes, 30, 35)!
    const edited = doc('Intro.', 'The brake shall engage.', 'The brake shall release.')
    const range = rangeFor(edited, quote)!
    expect(edited.textBetween(range.from, range.to)).toBe('brake')
    expect(edited.textBetween(range.to, range.to + 14)).toBe(' shall release')
  })

  it('reports a passage that is gone as detached', () => {
    const quote = quoteFor(twoBrakes, 5, 10)!
    expect(rangeFor(doc('The clutch shall engage.'), quote)).toBeNull()
  })
})
