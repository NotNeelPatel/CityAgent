// src/pages/Signup.tsx
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";


import {
  Card,
  CardFooter,
  CardTitle,
  CardHeader

} from "@/components/ui/card";

export function Signup() {
  return (
    <Card className="w-full w-96">
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle>Sign up to your account</CardTitle>
        </div>
        <Button variant="link" asChild>
          <Link to="/login">Sign Up</Link>
        </Button>
      </CardHeader>
    
      <CardFooter className="flex-col gap-2">
        <Button type="submit" className="w-full">
          Sign up with Outlook
        </Button>
        <Button variant="outline" className="w-full">
          Sign up with Google
        </Button>
      </CardFooter>
    </Card>
  );
}