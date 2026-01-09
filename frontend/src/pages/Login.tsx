import { useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { IconBrandGithubFilled, IconBrandGoogleFilled, IconBrandWindowsFilled } from "@tabler/icons-react";
import { Card, CardFooter, CardHeader, CardDescription, CardTitle } from "@/components/ui/card";

export function Login() {
  const { signInWithGoogle, signInWithAzure, user, loading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as any)?.from || "/search";

  useEffect(() => {
    if (!loading && user) {
      navigate(from, { replace: true });
    }
  }, [loading, user, navigate, from]);

  return (
    <div className="flex h-screen w-full justify-center items-center">
      <Card className="m-6 w-96">
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle className="text-2xl">Welcome to CityAgent</CardTitle>
            <CardDescription>
              Login to continue
            </CardDescription>
          </div>
        </CardHeader>

        <CardFooter className="flex gap-2">
          <Button size="lg" className="flex-1" onClick={signInWithGoogle} disabled={loading}>
            <IconBrandGoogleFilled className="size-6" />
          </Button>
          <Button size="lg" className="flex-1" onClick={signInWithAzure} disabled>
            <IconBrandWindowsFilled className="size-6" />
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
