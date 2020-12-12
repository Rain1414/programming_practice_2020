"""
Вспомогательные классы
"""
from typing import NewType, NamedTuple, Optional
from dataclasses import dataclass
# Тип, который соответствует частотам радиосигнала
FrequencyType = NewType("FrequencyType", float)

# Тип, который соотвествует id блока памяти
MemorySegmentID = NewType("MemorySegmentID", int)


class MemoryBlock(NamedTuple):
    """
    Блок памяти характеризующийся уникальным id,
    """
    memory_id: MemorySegmentID
    block_start: int
    block_end: int

    @property
    def size(self):
        return self.block_end - self.block_start


@dataclass
class Radiosignal:
    """
    Класс, содержащий информацию о передаваемом радиосигнале.
    """
    id_transmitter: int  # id передатчика
    id_receiver: int  # id приёмника
    memory: MemoryBlock  # частота сигнала несущей [МГц]
    frequency: FrequencyType  # блок памяти, в котором расположена информация, зашифрованная в сигнале
    id_antenna_receiver: Optional[int] = None  # id антенны приёмника, которая должна принять сигнал. Если Потребителем

    # не указано при отправке, то сигнал придёт на антенну, которая удовлетворяет другим условиям

    def __eq__(self, other):
        return ((self.id_transmitter == other.id_transmitter) and (
            self.id_receiver == other.id_receiver) and (
                self.memory == other.memory) and (
                    self.frequency == other.frequency) and (
                        self.id_antenna_receiver == other.id_antenna_receiver))


class ListenEtherTask(NamedTuple):
    """
    Класс канала, который создаётся Потребителем для приёма сигнала и ретрансляции.
    Если канал используется для ретрансляции, то задаются frequency_transmission_relay, id_destination_relay,
    id_antenna_destination_relay, save_relayed_signals_locally_relay.
    """
    # частота приёма сигнала
    frequency_recipiency: FrequencyType
    # id антенны приёмника, которая должна принять сигнал
    id_antenna_receiver: Optional[int] = None
    # частота, на которой будет проводиться отправка сигнала при ретрасляции
    frequency_transmission_relay: Optional[FrequencyType] = None
    # id приёмника, на который будет отправлен сигнал при ретрансляции
    id_destination_relay: Optional[int] = None
    # id антенны приёмника, на которую будет отправлен сигнал при ретрансляции
    id_antenna_destination_relay: Optional[int] = None
    # переменная для сохранения в локальных Потребителях радиосвязи сигналов при ретрансляции
    # False - в локальных Потребителях радиосвязи при ретрансляции НЕ будут сохраняться ретранслируемые сигналы;
    # True - в противном случае
    save_relayed_signals_locally_relay: bool = False

    def __eq__(self, other):
        return ((self.frequency_recipiency == other.frequency_recipiency) and (
            self.frequency_transmission_relay == other.frequency_transmission_relay) and (
                self.id_destination_relay == other.id_destination_relay) and (
                    self.save_relayed_signals_locally_relay == other.save_relayed_signals_locally_relay) and (
                        self.id_antenna_receiver == other.id_antenna_receiver) and (
                            self.id_antenna_destination_relay == other.id_antenna_destination_relay))
