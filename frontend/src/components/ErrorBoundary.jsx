import React from "react";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, message: "" };
  }
  static getDerivedStateFromError(err) {
    return { hasError: true, message: err?.message || "Kutilmagan xato" };
  }
  componentDidCatch(err, info) {
    // eslint-disable-next-line no-console
    console.error("ErrorBoundary:", err, info);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-background p-6">
          <div className="max-w-md w-full text-center space-y-4">
            <div className="text-6xl">💔</div>
            <h1 className="text-2xl font-heading font-semibold">Xato yuz berdi</h1>
            <p className="text-sm text-muted-foreground">{this.state.message}</p>
            <button
              data-testid="err-reload"
              onClick={() => window.location.reload()}
              className="px-5 py-3 rounded-2xl bg-primary text-white font-medium"
            >
              Qayta yuklash
            </button>
            <p className="text-[11px] text-muted-foreground pt-4">FIDEM — Halal Matchmaking</p>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
