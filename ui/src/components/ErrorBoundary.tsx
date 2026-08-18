import { Component, type ErrorInfo, type ReactNode } from 'react'
import { Link } from 'react-router'

type Props = { children: ReactNode }
type State = { error: Error | null }

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Page error:', error, info.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[16rem] p-8">
          <h2 className="text-lg font-semibold text-foreground mb-2">Something went wrong</h2>
          <p className="text-sm text-muted-foreground mb-4 max-w-md text-center">
            {this.state.error.message || 'An unexpected error occurred while loading this page.'}
          </p>
          <Link to="/" className="text-sm font-medium text-primary hover:text-primary/80">
            Back to Dashboard
          </Link>
        </div>
      )
    }
    return this.props.children
  }
}
