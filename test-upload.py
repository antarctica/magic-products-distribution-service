"""
This is temporary script for validating SharePoint works as we expect and that all actions/use-cases can be sufficently
automated. Code has larely be taken from the MAGIC-PDC Data Workflows PoC, and adapted to work standalone.

Once successful, this code will be significantly refactored into proper methods, classes and modules, along with tests
and code linting, etc.
"""

import json
import base64
import uuid
from typing import Dict, List
from http import client as http
from pathlib import Path

import quickxorhash
import requests
from requests import HTTPError
from msal import PublicClientApplication


record_id: str = "4a36ea8b-d4d8-4537-b46c-92f271ded940"
aretefact_path: Path = Path("./test-artefact.txt")

sharepoint_site_id: str = (
    "nercacuk.sharepoint.com,0561c437-744c-470a-887e-3d393e88e4d3,63825c43-db1b-40ca-a717-0365098c70c0"
)
sharepoint_drive_id: str = "b!N8RhBUx0CkeIfj05Pojk00NcgmMb28pApxcDZQmMcMBzlP8HkrS0TKveYyZFGRd3"
sharepoint_list_id: str = "07ff9473-b492-4cb4-abde-632645191777"

auth_client_tenancy: str = "https://login.microsoftonline.com/b311db95-32ad-438f-a101-7ba061712a4e"
auth_client_id: str = "36661990-3367-40dc-b7e7-04f80f8ac894"
auth_client_scopes: List[str] = ["https://graph.microsoft.com/Files.ReadWrite.All"]

auth_client_public: PublicClientApplication = PublicClientApplication(
    client_id=auth_client_id, authority=auth_client_tenancy
)

auth_token: str = ""
directory_item_id: str = ""
file_item: Dict[str, str] = {}


def get_authentication_token() -> str:
    auth_flow = auth_client_public.initiate_device_flow(scopes=auth_client_scopes)
    input(
        f"To sign-in, visit 'https://microsoft.com/devicelogin', enter this code '{auth_flow['user_code']}' and then press [enter] ..."
    )
    auth_payload = auth_client_public.acquire_token_by_device_flow(auth_flow)
    print(auth_payload["access_token"])
    return auth_payload["access_token"]


def create_directory(directory_path: str, record_id: str) -> str:
    try:
        directory_item_data: Optional[dict] = None
        directory_item = requests.get(
            url=f"https://graph.microsoft.com/v1.0/drives/{sharepoint_drive_id}/root:/{directory_path}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        if directory_item.ok:
            print(f"Directory '{directory_path}' already exists - skipping creation")
            directory_item_data = directory_item.json()
        elif directory_item.status_code == http.NOT_FOUND:
            print(f"Creating directory for '{directory_path}'")
            create_directory_item = requests.post(
                url=f"https://graph.microsoft.com/v1.0/drives/{sharepoint_drive_id}/root/children",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "name": directory_path,
                    "folder": {},
                    "@microsoft.graph.conflictBehavior": "fail",
                },
            )
            create_directory_item.raise_for_status()
            directory_item_data = create_directory_item.json()
            print(f"Directory '{directory_path}' created")

            directory_list_item = requests.get(
                url=f"https://graph.microsoft.com/v1.0/drives/{sharepoint_drive_id}/items/{directory_item_data['id']}/listitem",
                headers={"Authorization": f"Bearer {auth_token}"},
            )
            directory_list_item.raise_for_status()
            directory_list_item_data = directory_list_item.json()

            directory_list_item_fields = requests.patch(
                url=f"https://graph.microsoft.com/v1.0/sites/{sharepoint_site_id}/lists/{sharepoint_list_id}/items/{directory_list_item_data['id']}/fields",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={"resource_id": record_id, "artefact_id": "-"},
            )
            directory_list_item_fields.raise_for_status()
            print(f"Metadata for directory '{directory_path}' set")
        else:
            directory_item.raise_for_status()
    except HTTPError as e:
        print(e)
        print(e.response.json())
        raise RuntimeError(f"Unable to create directory '{directory_path}'")

    try:
        return directory_item_data["id"]
    except KeyError:
        raise RuntimeError(f"Unable to get item identifier for directory '{directory_path}'")


def upload_file(file_path: Path, folder_id: str, record_id: str) -> Dict[str, str]:
    try:
        file_item_data: Optional[dict] = None

        file_item = requests.get(
            url=f"https://graph.microsoft.com/v1.0/drives/{sharepoint_drive_id}/items/{folder_id}:/{file_path.name}:",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        if file_item.ok:
            file_item_data = file_item.json()
            print(
                f"File artefact '{file_path}' already exists at destination '{file_item_data['webUrl']}' - skipping upload"
            )
        elif file_item.status_code == http.NOT_FOUND:
            # https://stackoverflow.com/a/60467652
            upload_session = requests.post(
                url=f"https://graph.microsoft.com/v1.0/drives/{sharepoint_drive_id}/items/{folder_id}:/{file_path.name}:/createUploadSession",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={"@microsoft.graph.conflictBehavior": "fail"},
            )
            upload_session.raise_for_status()
            upload_session_data = upload_session.json()

            with open(file_path, "rb") as src_file:
                total_file_size = file_path.stat().st_size
                chunk_size = 327680  # set by Microsoft (≈4kB)
                chunks_count = total_file_size // chunk_size
                chunks_leftover = total_file_size - (chunk_size * chunks_count)

                # ensure there's at least one chunk for files under 320kB
                if chunks_count == 0:
                    chunks_count = 1

                for chunk_index in range(0, chunks_count + 1):
                    print(f"Processing chunk [{chunk_index}/{chunks_count}]", flush=True)

                    chunk_data = src_file.read(chunk_size)
                    if not chunk_data:
                        break

                    # calculate range headers
                    range_start = chunk_index * chunk_size
                    range_end = range_start + chunk_size
                    if (chunk_index == chunks_count) or (chunk_index == 0 and chunks_count == 1):
                        range_end = range_start + chunks_leftover
                    print(f"bytes {range_start}-{range_end - 1}/{total_file_size}")
                    headers = {
                        "Content-Length": str(chunk_size),
                        "Content-Range": f"bytes {range_start}-{range_end - 1}/{total_file_size}",
                    }

                    headers["Authorization"] = f"Bearer {auth_token}"
                    chunk_upload = requests.put(
                        url=upload_session_data["uploadUrl"],
                        data=chunk_data,
                        headers=headers,
                    )
                    chunk_upload.raise_for_status()

            file_item_data: dict = chunk_upload.json()
            print(f"File artefact '{file_path}' uploaded as '{file_item_data['webUrl']}'")

            # set file item metadata
            try:
                file_list_lookup = requests.get(
                    url=f"https://graph.microsoft.com/v1.0/drives/{sharepoint_drive_id}/items/{file_item_data['id']}/listitem",
                    headers={"Authorization": f"Bearer {auth_token}"},
                )
                file_list_lookup.raise_for_status()
                file_list_lookup_data = file_list_lookup.json()
            except HTTPError as e:
                print(e)
                print(e.response.json())
                raise RuntimeError("Unable to get metadata for file artefact file item")
            try:
                file_list_id: str = file_list_lookup_data["id"]
            except KeyError:
                raise RuntimeError("Unable to get file item list ID for file artefact")
            try:
                file_list_item = requests.patch(
                    url=f"https://graph.microsoft.com/v1.0/sites/{sharepoint_site_id}/lists/{sharepoint_list_id}/items/{file_list_id}/fields",
                    headers={"Authorization": f"Bearer {auth_token}"},
                    json={"resource_id": record_id, "artefact_id": str(uuid.uuid4())},
                )
                file_list_item.raise_for_status()
                print(f"Metadata for file artefact set")
            except HTTPError as e:
                print(e)
                print(e.response.json())
                raise RuntimeError("Unable to set metadata on file item for file artefact")

            try:
                file_list_lookup = requests.get(
                    url=f"https://graph.microsoft.com/v1.0/sites/{sharepoint_site_id}/lists/{sharepoint_list_id}/items/{file_list_id}",
                    headers={"Authorization": f"Bearer {auth_token}"},
                )
                file_list_lookup.raise_for_status()
                file_list_lookup_data = file_list_lookup.json()
            except HTTPError as e:
                print(e)
                print(e.response.json())
                raise RuntimeError("Unable to get metadata for file artefact file item")
            try:
                file_item_resource_id: str = file_list_lookup_data["fields"]["resource_id"]
                if file_item_resource_id != record_id:
                    raise ValueError("Resource identifier for file artefact set to the wrong value.")
            except KeyError:
                raise RuntimeError("No resource identifier set in file artefact item metadata")
            try:
                if "artefact_id" not in file_list_lookup_data["fields"]:
                    raise ValueError("No artefact identifier set for file.")
            except KeyError:
                raise RuntimeError("No metadata set for file item.")
        else:
            file_item.raise_for_status()
    except HTTPError as e:
        print(e)
        print(e.response.json())
        raise RuntimeError("Unable to upload file artefact")

    try:
        file_item_id: str = file_item_data["id"]
    except KeyError:
        raise RuntimeError("Unable to get file item identifier for file artefact")
    try:
        file_item_url: str = file_item_data["webUrl"]
    except KeyError:
        raise RuntimeError("Unable to get file item URL for file artefact")
    try:
        file_item_hash: str = file_item_data["file"]["hashes"]["quickXorHash"]
    except KeyError:
        raise RuntimeError("Unable to get file item hash for file artefact")

    # want to get custom fields from list as well
    try:
        file_list_lookup = requests.get(
            url=f"https://graph.microsoft.com/v1.0/drives/{sharepoint_drive_id}/items/{file_item_data['id']}/listitem",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        file_list_lookup.raise_for_status()
        file_list_lookup_data = file_list_lookup.json()
    except HTTPError as e:
        print(e)
        print(e.response.json())
        raise RuntimeError("Unable to get metadata for file artefact file item")
    try:
        file_item_artefact_id: str = file_list_lookup_data["fields"]["artefact_id"]
    except KeyError:
        raise RuntimeError("Unable to get artefact identifier for file item.")

    # verify hash
    quickxor = quickxorhash.quickxorhash()
    quickxor_block_size = 2**20
    with open(file_path, mode="rb") as hash_file:
        while True:
            data = hash_file.read(quickxor_block_size)
            if not data:
                break
            quickxor.update(data)
    quickxor_hash = base64.b64encode(quickxor.digest()).decode()
    if file_item_hash != quickxor_hash:
        # TODO: Split into two checks, if file exists assume file should be updated, if uploading assuming upload failed
        raise RuntimeError("Hash for uploaded file item does not match file artefact.")

    return {
        "file_item_id": file_item_id,
        "file_item_url": file_item_url,
        "file_item_hash": file_item_hash,
        "file_artefact_id": file_item_artefact_id,
    }


def make_download_proxy_item(file_item: Dict[str, str], record_id: str, media_type: str) -> Dict[str, str]:
    return {
        file_item["file_artefact_id"]: {
            "resource_id": record_id,
            "media_type": media_type,
            "href": file_item["file_item_url"],
        }
    }


def main() -> str:
    directory_item_id = create_directory(directory_path=record_id, record_id=record_id)
    file_item = upload_file(file_path=aretefact_path, folder_id=directory_item_id, record_id=record_id)
    # set_file_permissions()
    download_proxy_lookup_item = make_download_proxy_item(
        file_item=file_item, record_id=record_id, media_type="text/plain"
    )

    return json.dumps(download_proxy_lookup_item, indent=2)


if __name__ == "__main__":
    if auth_token == "":
        auth_token = get_authentication_token()

    output = main()
    print(output)
