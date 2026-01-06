import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

import {
  Card,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function Login() {
  return (
    <div className="flex h-screen w-full justify-center items-center">
      <Card className="m-6 w-96">
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>Login to your account</CardTitle>
          </div>
          <Button variant="link" asChild>
            <Link to="/signup">Sign Up</Link>
          </Button>
        </CardHeader>

        <CardFooter className="flex-col gap-2">
          <Button type="submit" className="w-full">
            Login with Outlook
          </Button>
          <Button variant="outline" className="w-full">
            Login with Google
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
