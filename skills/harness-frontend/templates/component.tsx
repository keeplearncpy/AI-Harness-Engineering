import React from 'react';

// === Types ===
interface {{ComponentName}}Props {
  // Define props here
  title?: string;
  className?: string;
}

// === Component ===
export const {{ComponentName}}: React.FC<{{ComponentName}}Props> = ({
  title = '{{ComponentName}}',
  className = '',
}) => {
  // --- State ---
  const [loading, setLoading] = React.useState<boolean>(true);
  const [error, setError] = React.useState<string | null>(null);
  const [data, setData] = React.useState<unknown>(null);

  // --- Effects ---
  React.useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        // TODO: Replace with actual API call
        // const response = await api.get{{ComponentName}}();
        // setData(response.data);
        setData(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // --- Render: Loading ---
  if (loading) {
    return (
      <div className={`animate-pulse p-4 ${className}`} role="status">
        <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
        <div className="h-4 bg-gray-200 rounded w-1/2" />
        <span className="sr-only">Loading...</span>
      </div>
    );
  }

  // --- Render: Error ---
  if (error) {
    return (
      <div className={`rounded-md bg-red-50 p-4 ${className}`} role="alert">
        <div className="flex">
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Error</h3>
            <p className="text-sm text-red-700 mt-1">{error}</p>
          </div>
        </div>
        <button
          onClick={() => window.location.reload()}
          className="mt-2 text-sm text-red-600 underline hover:text-red-500"
        >
          Retry
        </button>
      </div>
    );
  }

  // --- Render: Empty ---
  if (!data) {
    return (
      <div className={`text-center py-12 ${className}`}>
        <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
        </svg>
        <h3 className="mt-2 text-sm font-medium text-gray-900">No data yet</h3>
        <p className="mt-1 text-sm text-gray-500">Get started by creating a new item.</p>
      </div>
    );
  }

  // --- Render: Data ---
  return (
    <div className={className}>
      <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
      {/* TODO: Render actual data */}
    </div>
  );
};

export default {{ComponentName}};
