from core.enums import FieldsTypes


class BaseIntegration:

    MASS_OPERATIONS_BATCH_SIZE = 100
    auth_fields_description = {"token": {"name": "Токен", "type": FieldsTypes.TEXT, "max_length": 255}}

    def get_object_available_fields(self) -> dict:
        raise NotImplementedError

    def create_new_objects(self, model, objects_list):
        create_batches_count = len(objects_list) // self.MASS_OPERATIONS_BATCH_SIZE + (
            1 if len(objects_list) % self.MASS_OPERATIONS_BATCH_SIZE else 0
        )

        for i in range(create_batches_count):
            model.objects.bulk_create(
                objects_list[
                    (0 + i * self.MASS_OPERATIONS_BATCH_SIZE) : (
                        self.MASS_OPERATIONS_BATCH_SIZE + i * self.MASS_OPERATIONS_BATCH_SIZE
                    )
                ]
            )

    def update_existing_objects(self, model, objects_list):
        update_batches_count = len(objects_list) // self.MASS_OPERATIONS_BATCH_SIZE + (
            1 if len(objects_list) % self.MASS_OPERATIONS_BATCH_SIZE else 0
        )

        for i in range(update_batches_count):
            model.objects.bulk_update(
                objects_list[
                    (0 + i * self.MASS_OPERATIONS_BATCH_SIZE) : (
                        self.MASS_OPERATIONS_BATCH_SIZE + i * self.MASS_OPERATIONS_BATCH_SIZE
                    )
                ],
                fields=self.get_object_available_fields().get(model, []),
            )

    def __init__(self, account):
        self.account = account

    def get_auth_token(self):
        return self.account.authorization_fields.get("token", "")
