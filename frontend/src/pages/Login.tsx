import { useEffect, useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import {
  IconBrandGoogleFilled,
  IconBrandWindowsFilled,
} from "@tabler/icons-react";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardDescription,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function Login() {
  const {
    signInWithGoogle,
    signInWithAzure,
    signInWithPassword,
    user,
    loading,
  } = useAuth();

  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const from = (location.state as { from?: string } | null)?.from || "/search";

  useEffect(() => {
    if (!loading && user) {
      navigate(from, { replace: true });
    }
  }, [loading, user, navigate, from]);

  const handlePasswordLogin = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setErrorMessage("");
    setSubmitting(true);

    const { error } = await signInWithPassword(email, password);

    if (error) {
      setErrorMessage(error.message);
      setSubmitting(false);
      return;
    }

    setSubmitting(false);
  };

  const handleGoogleLogin = async () => {
    setErrorMessage("");
    const { error } = await signInWithGoogle();

    if (error) {
      setErrorMessage(error.message);
    }
  };

  const handleAzureLogin = async () => {
    setErrorMessage("");
    const { error } = await signInWithAzure();

    if (error) {
      setErrorMessage(error.message);
    }
  };

  return (
    <div className="flex min-h-svh w-full items-center justify-center p-6">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-2xl">Welcome to CityAgent</CardTitle>
          <CardDescription>Login to continue</CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={handlePasswordLogin} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading || submitting}
                required
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between gap-2">
                <Label htmlFor="password">Password</Label>
              </div>

              <Input
                id="password"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading || submitting}
                required
              />
            </div>

            {errorMessage ? (
              <p className="text-sm text-destructive">{errorMessage}</p>
            ) : null}

            <Button
              type="submit"
              className="w-full"
              size="lg"
              disabled={loading || submitting}
            >
              {submitting ? "Signing in..." : "Sign in"}
            </Button>
          </form>
        </CardContent>

        <CardFooter className="flex flex-col gap-4">
          <div className="flex w-full items-center gap-2">
            <div className="h-px flex-1 bg-border" />
            <span className="text-xs text-muted-foreground">OR</span>
            <div className="h-px flex-1 bg-border" />
          </div>

          <div className="flex w-full gap-2">
            <Button
              type="button"
              variant="outline"
              size="lg"
              className="flex-1"
              onClick={handleGoogleLogin}
              disabled={loading || submitting}
            >
              <IconBrandGoogleFilled className="size-5" />
            </Button>

            <Button
              type="button"
              variant="outline"
              size="lg"
              className="flex-1"
              onClick={handleAzureLogin}
              disabled
            >
              <IconBrandWindowsFilled className="size-5" />
            </Button>
          </div>

          <p className="text-center text-sm text-muted-foreground">
            Don&apos;t have an account?{" "}
            <Link to="/sign-up" className="text-foreground hover:underline">
              Sign up
            </Link>
          </p>
        </CardFooter>
      </Card>
    </div>
  );
}