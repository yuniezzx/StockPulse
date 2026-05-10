import { z } from "zod";

export const registerBodySchema = z.object({
  username: z.string().min(3).max(32),
  password: z.string().min(8).max(128),
});

export const loginBodySchema = z.object({
  username: z.string().min(3).max(32),
  password: z.string().min(8).max(128),
});

export const publicUserSchema = z.object({
  id: z.string().uuid(),
  username: z.string(),
  createdAt: z.string(),
});

export const authSuccessSchema = z.object({
  token: z.string(),
  user: publicUserSchema,
});
export const meResponseSchema = z.object({
  user: publicUserSchema,
});

export type RegisterBody = z.infer<typeof registerBodySchema>;
export type LoginBody = z.infer<typeof loginBodySchema>;
export type PublicUser = z.infer<typeof publicUserSchema>;
export type AuthSuccess = z.infer<typeof authSuccessSchema>;
export type MeResponse = z.infer<typeof meResponseSchema>;
