import { useLocation } from "react-router-dom";

export default function PlaceholderPage() {
  const { pathname } = useLocation();
  return (
    <div className="flex flex-col items-center justify-center h-full gap-2 p-6">
      <h2 className="text-xl font-semibold">建设中</h2>
      <p className="text-sm text-muted-foreground">{pathname}</p>
    </div>
  );
}
