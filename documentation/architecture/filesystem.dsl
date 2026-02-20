/*
 * filesystem.dsl — Level 4 deep backend filesystem view
 *
 * OWNERSHIP CONTRACT:
 *   - This file is owned by developers.
 *   - It MUST be updated whenever a Python or Svelte file is added, removed,
 *     or moved within the backend or frontend containers.
 *   - This file NEVER defines model elements (no `= component`, no `= container`,
 *     no `=` assignments of any kind). It contributes only a view.
 *   - All model elements (components, containers, relationships) are defined in
 *     workspace.dsl. This file is !included inside the views {} block of
 *     workspace.dsl, so it has access to all elements defined there.
 *
 * To add a file: add its component ID to the include list below.
 * To remove a file: remove its component ID from the include list below.
 * Never define new elements here.
 */

component backend "BackendFilesystem" "C4 Level 4 — Python module layout for the FastAPI backend, grouped by package directory." {
    include mainPy
    include routesPy
    include registryLoaderPy
    include databasePy
    include archiveReaderPy
    include trajectoryPy
    include reportSerializerPy
    autoLayout
}
