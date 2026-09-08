import { Component, type ReactNode, type ErrorInfo } from 'react';
import { WarningOctagon } from '@phosphor-icons/react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('FactLoom UI Error Caught:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-[50vh] flex flex-col items-center justify-center p-8 text-center max-w-xl mx-auto space-y-4">
          <div className="p-4 rounded-full bg-[var(--loom-contradiction)]/10 text-[var(--loom-contradiction)] border border-[var(--loom-contradiction)]/30">
            <WarningOctagon size={36} />
          </div>
          <h2 className="font-display text-2xl font-bold text-[var(--loom-paper)]">
            UI Rendering Encountered an Issue
          </h2>
          <p className="font-mono-tabular text-xs text-[var(--loom-contradiction)] bg-[var(--loom-card)] p-3 rounded border border-[var(--loom-card-border)] w-full text-left overflow-x-auto">
            {this.state.error?.message || 'Unknown error'}
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
            className="px-4 py-2 rounded bg-[var(--loom-surface)] border border-[var(--loom-hairline)] text-xs text-[var(--loom-paper)] hover:bg-[var(--loom-card)]"
          >
            Reload Interface
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
