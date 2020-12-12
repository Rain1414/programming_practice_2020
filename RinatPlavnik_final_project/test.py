from global_system import (RadioTransmissionMediumConsumerProperties, RadioTransmissionMediumSystem)
from local_system import (
    RadiotransmissionConsumerProperties, TransmitReceiveDeviceProperties, RadiotransmissionSystem)
from auxiliary_classes import MemoryBlock, MemorySegmentID, Radiosignal


def test_signals_are_in_receivers():
    """
    Тест, который проверяет, доходят ли сигналы от передатчиков до приёмников
    через систему радиосвязи с учётом ретрансляции сигналов.
    Имеется 3 космических аппарата (КА).
    КА 1 только отправляет сигналы на КА 2 и КА 3,
    КА 2 ретранслирует сигналы на КА 3 и сам отправляет сигналы на КА 3,
    КА 3 только принимает сигналы.
    """
    # Создаём глобальную Систему радиосвязи
    radiotransmission_medium_system = RadioTransmissionMediumSystem()

    # Задаём свойства глобальных Потребителей радиосвязи
    # Id потребителей должна задавать другая система, у которой есть доступ ко всем аппарат. Здесь пока задаю руками
    global_consumer1_properties = RadioTransmissionMediumConsumerProperties(frequency=100, id_consumer=1)
    global_consumer2_properties = RadioTransmissionMediumConsumerProperties(frequency=100, id_consumer=2)
    global_consumer3_properties = RadioTransmissionMediumConsumerProperties(frequency=150, id_consumer=3)

    # Регистрируем глобальных Потребителей в Системе
    global_consumer1 = radiotransmission_medium_system.register_consumer(global_consumer1_properties)
    global_consumer2 = radiotransmission_medium_system.register_consumer(global_consumer2_properties)
    global_consumer3 = radiotransmission_medium_system.register_consumer(global_consumer3_properties)

    # Создаём локальные Системы радиосвязи для каждого КА
    radiotransmission_system_1 = RadiotransmissionSystem(global_consumer1)
    radiotransmission_system_2 = RadiotransmissionSystem(global_consumer2)
    radiotransmission_system_3 = RadiotransmissionSystem(global_consumer3)

    # Задаём свойства антенн для каждого КА
    antenna_properties = TransmitReceiveDeviceProperties(
        channel_capacity_transmit=100,
        channel_capacity_receive=100,
        frequency_range_min=50,
        frequency_range_max=200,
        consumption=10,
        mass=1,
        guid_time=1,
        koef_receive=1,
        koef_transmit=1,
        receive_power_consumption=1,
        transmit_power_consumption=1,
        receive_radio_noise=1,
        offset_angle=1)

    # Задаём свойства локальных Потребителей радиосвязи
    consumer1_properties1 = RadiotransmissionConsumerProperties(frequency=100)
    consumer2_properties1 = RadiotransmissionConsumerProperties(frequency=150)
    consumer3_properties1 = RadiotransmissionConsumerProperties(frequency=150)

    # Создаём локальных Потребителей радиосвязи для каждого КА
    consumer_1 = radiotransmission_system_1.register_consumer(consumer1_properties1)
    consumer_2 = radiotransmission_system_2.register_consumer(consumer2_properties1)
    consumer_3 = radiotransmission_system_3.register_consumer(consumer3_properties1)

    # Создаём антенну для каждого КА
    radiotransmission_system_1.add_device(antenna_properties)
    radiotransmission_system_1.add_device(antenna_properties)
    radiotransmission_system_2.add_device(antenna_properties)
    radiotransmission_system_2.add_device(antenna_properties)
    radiotransmission_system_2.add_device(antenna_properties)
    radiotransmission_system_3.add_device(antenna_properties)
    radiotransmission_system_3.add_device(antenna_properties)

    # Локальные Потребители отправляют сигналы

    # Сигнал будет отправлен с КА 1 на КА 2 и будет ретранслирован на КА 3
    signal_121 = consumer_1.send_signal(id_receiver=2, memory=MemoryBlock(MemorySegmentID(121), 3, 4), frequency=100)
    # Сигнал будет отправлен с КА 1 на КА 2, но КА 2 не сможет его принять, так как не слушает на данной частоте
    signal_122 = consumer_1.send_signal(id_receiver=2, memory=MemoryBlock(MemorySegmentID(122), 5, 6), frequency=150)
    # Сигнал будет отправлен с КА 1 на КА 3
    signal_131 = consumer_1.send_signal(id_receiver=3, memory=MemoryBlock(MemorySegmentID(131), 7, 8), frequency=150)
    # Сигнал будет отправлен с КА 2 на КА 3
    signal_233 = consumer_2.send_signal(id_receiver=3, memory=MemoryBlock(MemorySegmentID(233), 17, 18), frequency=100)

    # Метод assign_device должен вызываться Менеджером сеансов связи, в упрощенной модели его нет
    # Назначаются антенны на отправку сигналов
    # id_antenna_receiver - id принимающей антенны указан для тех сигналов,
    # которые должны в итоге дойти до локального Потребителя
    radiotransmission_system_1.assign_device_as_transmitter(memory_block=signal_121.memory,
                                                            id_antenna=0,
                                                            id_receiver=signal_121.id_receiver,
                                                            frequency=signal_121.frequency, id_antenna_receiver=1)
    radiotransmission_system_1.assign_device_as_transmitter(memory_block=signal_122.memory,
                                                            id_antenna=1,
                                                            id_receiver=signal_122.id_receiver,
                                                            frequency=signal_122.frequency, id_antenna_receiver=0)
    radiotransmission_system_1.assign_device_as_transmitter(memory_block=signal_131.memory,
                                                            id_antenna=1,
                                                            id_receiver=signal_131.id_receiver,
                                                            frequency=signal_131.frequency, id_antenna_receiver=1)
    radiotransmission_system_1.assign_device_as_transmitter(memory_block=signal_233.memory,
                                                            id_antenna=0,
                                                            id_receiver=signal_233.id_receiver,
                                                            frequency=signal_233.frequency, id_antenna_receiver=0)

    # Локальный потребитель заявляет, что ретранслирует сигнал
    consumer_2.i_am_repeater(id_destination_relay=3,
                             frequency_recipiency=100,
                             frequency_transmission_relay=150,
                             save_relayed_signals_locally_relay=True)

    # Этот метод должен вызываться Менеджером сеансов связи
    # Назначаются антенны на ретрансляцию сигналов
    radiotransmission_system_2.assign_device_as_repeater(id_antenna_in=1,
                                                         id_antenna_out=2,
                                                         id_destination_relay=3,
                                                         id_antenna_destination_relay=1,
                                                         frequency_in=100,
                                                         frequency_out=150,
                                                         save_relayed_signals_locally_relay=True)

    # Локальные Потребители заявляют, что слушают эфир
    consumer_3.listen_ether(frequency_recipiency=100)
    consumer_3.listen_ether(frequency_recipiency=150)

    # Назначаются антенны на приём сигналов
    radiotransmission_system_3.assign_device_as_receiver(id_antenna=0, frequency=100)
    radiotransmission_system_3.assign_device_as_receiver(id_antenna=1, frequency=150)

    print("Локальный потребитель 1 отправляет данные сигналы", consumer_1.dict_id_receiver_signals_to_send)
    print("Локальный потребитель 2 отправляет данные сигналы", consumer_2.dict_id_receiver_signals_to_send)
    print("Локальный потребитель 3 отправляет данные сигналы", consumer_3.dict_id_receiver_signals_to_send)

    # Первый имитационный шаг локальных Систем (идёт только отправка сигналов в глобальные Потребители радиосвязи)
    radiotransmission_system_1.imitation_step(duration=1)
    radiotransmission_system_2.imitation_step(duration=1)
    radiotransmission_system_3.imitation_step(duration=1)

    # Первый имитационный шаг глобальной Системы (идёт передача сигналов между глобальными Потребителями)
    radiotransmission_medium_system.imitation_step(duration=1)

    # Проверяем, что сигналы были переданы глобальным Потребителям радиосвязи
    # Сигнал, будет ретранслирован на КА 3 и который сохранился в глобальном потребителе 2
    assert MemoryBlock(MemorySegmentID(121), 3, 4) in [
        signal.memory for list_of_radiosignals in global_consumer2.dict_frequency_signal_to_receive.values()
        for signal in list_of_radiosignals]
    # Сигнал будет отправлен с КА 2 на КА 3
    assert MemoryBlock(MemorySegmentID(233), 17, 18) in [
        signal.memory for list_of_radiosignals in global_consumer3.dict_frequency_signal_to_receive.values()
        for signal in list_of_radiosignals]
    # Сигнал будет отправлен с КА 1 на КА 3
    assert MemoryBlock(MemorySegmentID(131), 7, 8) in [
        signal.memory for list_of_radiosignals in global_consumer3.dict_frequency_signal_to_receive.values()
        for signal in list_of_radiosignals]
    # Сигнал будет отправлен с КА 1 на КА 2, но КА 2 не сможет его принять, так как не слушает на данной частоте
    assert MemoryBlock(MemorySegmentID(122), 5, 6) not in [
        signal.memory for list_of_radiosignals in global_consumer2.dict_frequency_signal_to_receive.values()
        for signal in list_of_radiosignals]

    # Запускаем передачу сигналов от глобальных Потребителей в локальные Системы радиосвязи
    radiotransmission_system_1.finalize_step()
    radiotransmission_system_2.finalize_step()
    radiotransmission_system_3.finalize_step()

    # Проверяем, что сигналы локальным Системам радиосвязи были переданы правильно
    assert radiotransmission_system_1.dict_id_device_memory_blocks_to_receive == {}
    assert radiotransmission_system_2.dict_id_device_memory_blocks_to_receive == {}
    assert radiotransmission_system_3.dict_id_device_memory_blocks_to_receive == {0: [MemoryBlock(MemorySegmentID(233),
                                                                                                  17, 18)],
                                                                                  1: [MemoryBlock(MemorySegmentID(121),
                                                                                                  3, 4),
                                                                                      MemoryBlock(MemorySegmentID(131),
                                                                                                  7, 8)]}
    print("Локальный Потребитель 1 после шага моделирования получил эти сигналы",
          consumer_1.get_antennas_signals(0) + consumer_1.get_antennas_signals(1))
    print("Локальный Потребитель 2 после шага моделирования получил эти сигналы",
          consumer_2.get_antennas_signals(0) + consumer_2.get_antennas_signals(1) + consumer_2.get_antennas_signals(2))
    print("Локальный Потребитель 3 после шага моделирования получил эти сигналы",
          consumer_3.get_antennas_signals(0) + consumer_3.get_antennas_signals(1))


test_signals_are_in_receivers()
