/**
 * Mirrors backend app.domain.value_objects.edit_operation.EditOperation.
 * The frontend never invents an operation name — this type only exists so
 * TypeScript can check what the backend's catalog endpoint hands back.
 */
export type EditOperation =
  | "wave"
  | "peace_sign"
  | "thumbs_up"
  | "fist"
  | "smile"
  | "smile_with_teeth"
  | "closed_mouth"
  | "open_eyes"
  | "closed_eyes"
  | "red_shirt"
  | "black_jacket"
  | "white_tshirt"
  | "blue_jeans"
  | "shorts"
  | "wristwatch"
  | "bracelet";
