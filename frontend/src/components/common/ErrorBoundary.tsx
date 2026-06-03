import { Component, type ReactNode } from 'react'

interface Props { children: ReactNode }
interface State { hasError: boolean; error: string }

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: '' }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error: error.message }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="container mt-5">
          <div className="alert alert-danger">
            <h5><i className="fa-solid fa-triangle-exclamation me-2"></i>오류 발생</h5>
            <p className="mb-2">{this.state.error}</p>
            <button className="btn btn-sm btn-outline-danger" onClick={() => this.setState({ hasError: false, error: '' })}>
              다시 시도
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
