# Hide404

means that you can use this service to find everything, ensuring there are no situations where something cannot be found.

## Description

Hide404 is a simple service that allows you to find everything.
This project can be quickly deployed after simple configuration without relying on other services like Redis, PostgreSQL, etc.

## Set up

- ### From source code

  1. Change the sample configuration file name from `config.toml.example` to `config.toml`
  2. Set up the configuration in `config.toml`.
     The configuration file already includes descriptions for all fields.
  3. run `pip install -r requirements.txt`
  4. run `python main.py`

- ### Docker
  - Will be added later

## API

- ### v1

  - > [GET] /api/v1/id

    - Description: Get a trace_id to add to the request body of any API that can be tracked
      <br>

  - > [GET] /api/v1/event/{event_id}

    - Description: Get an event details by its event_id(a trace_id that has been assigned to a event)
    - Path: `event_id`
      <br>

  - > [GET] /api/v1/file/{collection_name}

    - Description: Retrieve the list of files including their metadata in a specified collection
    - Path: `collection_name`
      <br>

  - > [GET] /api/v1/file/{collection_name}/{file_id}

    - Description: Retrieve a file's metadata from a specified collection
    - Path: `collection_name`, `file_id`
      <br>

  - > [POST] /api/v1/upload

    - Description: Upload a file to a specified collection directory. User can specify a trace_id in the request body to track the event
    - Headers: `Content-Type: multipart/form-data`
    - Form Data: `attachments (File)`, `collection_name (Text)`, `(Optional) trace_id (Text)`
      <br>

  - > [POST] /api/v1/learn

    - Description: Upload a file to a specified collection
    - Headers: `Content-Type: application/json`
    - body:
      ```json
      {
        "collection_name": "collection_name",
        "tag": "any_tag",
        "author": "mmqnym",
        "re": true
      }
      ```
      **Note**: `re` whether to relearn the collection if it already exists. This will delete the old collection and create a new one.
      <br>

  - > [POST] /api/v1/chat

    - Description: Chat with the model using a specified collection
    - Headers: `Content-Type: application/json`
    - body:
      ```json
      {
        "collection_name": "collection_name",
        "query": "context"
      }
      ```
      **Note**: You may want the model to remember previous conversations, and you can assign past context together to the context. But, it is recommended to set a text length limit.
      <br>

  - > [DELETE] /api/v1/forget

    - Description: Delete a specified collection from the vector store and the database
    - Headers: `Content-Type: application/json`
    - body:
      ```json
      {
        "collection_name": "security"
      }
      ```
      <br>

## Basic usage

1. Use `/api/v1/id` to get a `trace_id`
2. Use `/api/v1/upload` with the `collection_name` and `trace_id` to upload file(s)
3. Use `trace_id` to track the upload progress
4. After the upload is complete, use `/api/v1/learn` to learn the collection
5. Now, you can use `/api/v1/chat` to chat with the model using the collection you just learned

## License

[Apache 2.0 License](./LICENSE.md)
