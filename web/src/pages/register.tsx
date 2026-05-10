import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuthStore } from "@/store/auth";
import { register as registerApi } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";

export default function RegisterPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.login);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { token, user } = await registerApi({ username, password });
      setAuth(token, user);
      navigate("/");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) setError("该用户名已被使用");
        else if (err.status === 400) setError("用户名 3-32 位、密码至少 8 位");
        else setError(err.message || "注册失败，请稍后重试");
      } else {
        setError("网络错误，请检查 API 是否运行");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-background flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">StockPulse</CardTitle>
          <CardDescription>创建账户</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {error && (
              <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {error}
              </div>
            )}
            <div className="flex flex-col gap-2">
              <Label htmlFor="username">用户名</Label>
              <Input
                id="username"
                type="text"
                autoComplete="username"
                placeholder="3-32 位"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="h-11"
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="password">密码</Label>
              <Input
                id="password"
                type="password"
                autoComplete="new-password"
                placeholder="至少 8 位"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="h-11"
              />
            </div>
            <Button type="submit" className="mt-2 h-11 w-full" disabled={loading}>
              {loading ? "注册中..." : "注册"}
            </Button>
            <p className="text-muted-foreground text-center text-sm">
              已有账号？{" "}
              <Link to="/login" className="text-primary hover:underline">
                登录
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
