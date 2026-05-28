from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast

if TYPE_CHECKING:
  from ..models.success_response_success import SuccessResponseSuccess





T = TypeVar("T", bound="SuccessResponse")



@_attrs_define
class SuccessResponse:
    """ 
        Attributes:
            success (SuccessResponseSuccess | Unset):
     """

    success: SuccessResponseSuccess | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.success_response_success import SuccessResponseSuccess
        success: dict[str, Any] | Unset = UNSET
        if not isinstance(self.success, Unset):
            success = self.success.to_dict()


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
        })
        if success is not UNSET:
            field_dict["success"] = success

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.success_response_success import SuccessResponseSuccess
        d = dict(src_dict)
        _success = d.pop("success", UNSET)
        success: SuccessResponseSuccess | Unset
        if isinstance(_success,  Unset):
            success = UNSET
        else:
            success = SuccessResponseSuccess.from_dict(_success)




        success_response = cls(
            success=success,
        )


        success_response.additional_properties = d
        return success_response

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
