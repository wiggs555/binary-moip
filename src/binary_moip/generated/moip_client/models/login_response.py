from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset






T = TypeVar("T", bound="LoginResponse")



@_attrs_define
class LoginResponse:
    """ 
        Attributes:
            access_token (str | Unset):
            token_type (str | Unset):
            expires_in (int | Unset):
     """

    access_token: str | Unset = UNSET
    token_type: str | Unset = UNSET
    expires_in: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        access_token = self.access_token

        token_type = self.token_type

        expires_in = self.expires_in


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
        })
        if access_token is not UNSET:
            field_dict["accessToken"] = access_token
        if token_type is not UNSET:
            field_dict["tokenType"] = token_type
        if expires_in is not UNSET:
            field_dict["expiresIn"] = expires_in

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        access_token = d.pop("accessToken", UNSET)

        token_type = d.pop("tokenType", UNSET)

        expires_in = d.pop("expiresIn", UNSET)

        login_response = cls(
            access_token=access_token,
            token_type=token_type,
            expires_in=expires_in,
        )


        login_response.additional_properties = d
        return login_response

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
