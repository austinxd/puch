export default function PrivacyPolicy() {
  return (
    <div className="max-w-3xl mx-auto py-12 px-4">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Pol&iacute;tica de Privacidad</h1>
      <p className="text-sm text-gray-500 mb-8">Última actualización: 17 de febrero de 2026</p>

      <div className="space-y-6 text-gray-700 text-sm leading-relaxed">
        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">1. Información General</h2>
          <p>
            Brikia ("nosotros", "nuestro") es una empresa inmobiliaria con sede en Lima, Perú.
            Esta política de privacidad describe cómo recopilamos, usamos y protegemos la información
            personal que usted nos proporciona a través de nuestros servicios, incluyendo nuestro
            sitio web, panel de administración y asistente virtual de WhatsApp.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">2. Información que Recopilamos</h2>
          <p>Podemos recopilar la siguiente información:</p>
          <ul className="list-disc ml-6 mt-2 space-y-1">
            <li>Nombre y datos de contacto (teléfono, correo electrónico)</li>
            <li>Número de teléfono de WhatsApp cuando interactúa con nuestro asistente virtual</li>
            <li>Mensajes y conversaciones con nuestro asistente virtual</li>
            <li>Preferencias de búsqueda de propiedades (ubicación, precio, tipo)</li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">3. Uso de la Información</h2>
          <p>Utilizamos su información para:</p>
          <ul className="list-disc ml-6 mt-2 space-y-1">
            <li>Responder a sus consultas sobre propiedades inmobiliarias</li>
            <li>Proporcionarle recomendaciones personalizadas de propiedades</li>
            <li>Mejorar nuestros servicios y atención al cliente</li>
            <li>Contactarle respecto a propiedades de su interés</li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">4. WhatsApp y Servicios de Terceros</h2>
          <p>
            Nuestro asistente virtual opera a través de la API de WhatsApp Business de Meta.
            Al interactuar con nuestro asistente, su número de teléfono y mensajes son procesados
            de acuerdo con las políticas de Meta. También utilizamos servicios de inteligencia
            artificial (OpenAI) para generar respuestas relevantes. Los mensajes enviados son
            procesados por estos servicios para brindarle una mejor experiencia.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">5. Protección de Datos</h2>
          <p>
            Implementamos medidas de seguridad técnicas y organizativas para proteger su
            información personal contra acceso no autorizado, alteración, divulgación o
            destrucción. Sin embargo, ninguna transmisión por Internet es completamente segura.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">6. Retención de Datos</h2>
          <p>
            Conservamos sus datos personales y conversaciones mientras sea necesario para
            proporcionarle nuestros servicios o según lo requiera la ley. Puede solicitar
            la eliminación de sus datos en cualquier momento.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">7. Sus Derechos</h2>
          <p>Usted tiene derecho a:</p>
          <ul className="list-disc ml-6 mt-2 space-y-1">
            <li>Acceder a sus datos personales</li>
            <li>Rectificar datos inexactos</li>
            <li>Solicitar la eliminación de sus datos</li>
            <li>Oponerse al procesamiento de sus datos</li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">8. Contacto</h2>
          <p>
            Si tiene preguntas sobre esta política de privacidad o desea ejercer sus derechos,
            puede contactarnos a través de:
          </p>
          <ul className="list-disc ml-6 mt-2 space-y-1">
            <li>Correo: sergio@brikia.tech</li>
            <li>Sitio web: admin.brikia.tech</li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">9. Cambios en esta Política</h2>
          <p>
            Nos reservamos el derecho de actualizar esta política de privacidad en cualquier
            momento. Los cambios serán publicados en esta página con la fecha de actualización.
          </p>
        </section>
      </div>
    </div>
  )
}
